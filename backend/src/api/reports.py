"""Reports API — DB-backed (SOP 4 + SOP 1 + SOP 2 BE-side, BE-1/BE-2/BE-4).

Persistence model (DB-1 decision: reuse user_reports):
  * Path A (venue-bound):    user_reports.venue_id = <venue>
  * Path B (GPS standalone): user_reports.venue_id = NULL
  report_scope ("venue_bound" | "standalone") is derived from venue_id.

TTL lifecycle (SOP 2 / BE-4):
  * On submit: expires_at = NOW() + expires_in_minutes (default 120).
  * On confirmation: still_here extends expires_at by +30 min (active only);
    resolved sets status='resolved' immediately; other actions only record.
  * Periodic cleanup soft-expires active rows whose expires_at <= NOW()
    (see cleanup_expired_reports below; run via scheduler/worker).

Confirmation model (DB-2):
  * report_confirmations (report_id, user_id) UNIQUE — one confirmation per
    user per report. Upsert is idempotent; duplicate re-confirmations update
    the action + created_at without producing a duplicate row.

Auth: Bearer-auth required (g.user_id). user_reports.user_id is NOT NULL in
the DDL, so reports require an authenticated user. Standalone reports do not
bypass auth — only venue binding differs.

Fallback: when no DB is reachable (local dev on mocks), the in-memory mock
path is used and responses carry data_mode="mock" so the lineage is
observable, never silent.
"""

import json as _json
from datetime import timedelta
from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from auth import require_api_key, require_bearer_auth
from mock_data import REPORT_TEMPLATE, REPORTS

bp = Blueprint("reports", __name__)

# Aligned with openapi.yaml ReportSubmission.issue_type (9 entries).
ALLOWED_REPORT_TYPES = {
    "elevator_broken",
    "wheelchair_lift_broken",
    "toilet_out_of_order",
    "large_crowd",
    "long_waiting_time",
    "protest_or_blockage",
    "entrance_closed",
    "ramp_blocked",
    "closed_early",
}

ISSUE_TYPE_LABELS = {
    "elevator_broken": "Lift Broken",
    "wheelchair_lift_broken": "Wheelchair Lift Broken",
    "toilet_out_of_order": "Toilet out of service",
    "large_crowd": "Too Crowded",
    "long_waiting_time": "Long Waiting Time",
    "protest_or_blockage": "Protest / Blockage",
    "entrance_closed": "Entrance Blocked",
    "ramp_blocked": "Ramp Blocked",
    "closed_early": "Closed Early",
}

ALLOWED_CONFIRMATION_ACTIONS = {
    "still_here",
    "resolved",
    "not_sure",
    "still_out_of_order",
    "open_now",
}

DEFAULT_TTL_MINUTES = 120
STILL_HERE_EXTEND_MINUTES = 30

# TTL refresh / lifecycle constants
TTL_ACTIVE = "active"
TTL_RESOLVED = "resolved"
TTL_EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Mock helpers (fallback when no DB)
# ---------------------------------------------------------------------------

def _next_report_id() -> str:
    report_numbers = []
    for report in REPORTS:
        report_id = report.get("report_id", "")
        if report_id.startswith("r_"):
            try:
                report_numbers.append(int(report_id.removeprefix("r_")))
            except ValueError:
                continue
    next_number = max(report_numbers, default=500) + 1
    return f"r_{next_number}"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db():
    """Resolve the shared connection-pool transaction helper lazily.

    Imported inside the function so that collecting tests in a no-DB env never
    touches dbutils/pymysql (mirrors the lazy-import discipline in db.py).
    Returns the db module, or None if it is unavailable.
    """
    try:
        import db as _db_module
        # Touch db_transaction to confirm the pool path is wired; if dbutils
        # is absent, get_connection raises only when actually used, so this
        # import alone is safe.
        return _db_module
    except Exception:
        return None


def _issue_type_exists(cursor, issue_type: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM report_categories WHERE category_id = %s AND is_active = TRUE",
        (issue_type,),
    )
    return cursor.fetchone() is not None


def _serialize_report(row: dict) -> dict:
    """Map a user_reports row (with joined confirmation aggregate) to the
    OpenAPI Report DTO."""
    report = {
        "report_id": row["report_id"],
        "issue_type": row["issue_type"],
        "issue_type_label": ISSUE_TYPE_LABELS.get(row["issue_type"], row["issue_type"]),
        "venue_id": row.get("venue_id"),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "accuracy_m": float(row["accuracy_meters"]) if row.get("accuracy_meters") is not None else None,
        "anonymous": bool(row.get("anonymous", False)),
        "description": row.get("description"),
        "photos": _json.loads(row["photos"]) if row.get("photos") else [],
        "status": row["status"],
        "created_at": _iso_z(row.get("created_at")),
        "expires_at": _iso_z(row.get("expires_at")),
        "expires_in_minutes": _expires_in_minutes(row.get("expires_at")),
        "confirmations": {
            "count": int(row.get("confirmation_count", 0) or 0),
            "latest_action": row.get("latest_action"),
            "latest_action_at": _iso_z(row.get("latest_action_at")),
        },
        "badge_text": _badge_text(row),
        "report_scope": "venue_bound" if row.get("venue_id") else "standalone",
    }
    return report


def _iso_z(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        # MySQL DATETIME is naive; treat as UTC for a stable ISO string.
        if value.tzinfo is None:
            from datetime import timezone
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _expires_in_minutes(expires_at):
    if expires_at is None or not hasattr(expires_at, "timestamp"):
        return 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    exp = expires_at
    if exp.tzinfo is None:
        from datetime import timezone as _tz
        exp = exp.replace(tzinfo=_tz.utc)
    delta = (exp - now).total_seconds() / 60
    return max(0, int(delta))


def _badge_text(row) -> str:
    status = row.get("status")
    if status == TTL_RESOLVED:
        return "Resolved"
    if status == TTL_EXPIRED:
        return "Expired"
    count = int(row.get("confirmation_count", 0) or 0)
    return "Multiple users confirm" if count >= 3 else "Live report"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.get("/api/v1/reports")
@require_api_key
def list_reports():
    """List active community reports (Path A + Path B unified)."""
    db = _db()
    if db is not None:
        try:
            with db.db_cursor() as cur:
                # Active reports only, with confirmation aggregate + latest action.
                cur.execute(
                    "SELECT ur.report_id, ur.user_id, ur.venue_id, ur.issue_type, "
                    "ur.latitude, ur.longitude, ur.accuracy_meters, ur.anonymous, "
                    "ur.description, ur.photos, ur.status, ur.created_at, ur.expires_at, "
                    "COALESCE(c.cnt, 0) AS confirmation_count, "
                    "c.latest_action, c.latest_action_at "
                    "FROM user_reports ur "
                    "LEFT JOIN ("
                    "  SELECT report_id, COUNT(*) AS cnt, "
                    "         MAX(action) AS latest_action, MAX(created_at) AS latest_action_at "
                    "  FROM report_confirmations GROUP BY report_id"
                    ") c ON c.report_id = ur.report_id "
                    "WHERE ur.status = %s "
                    "ORDER BY ur.created_at DESC",
                    (TTL_ACTIVE,),
                )
                rows = cur.fetchall()
            return jsonify({
                "count": len(rows),
                "items": [_serialize_report(r) for r in rows],
                "data_mode": "db",
            })
        except Exception:
            pass  # fall through to mock

    # --- Mock fallback ---
    active = [r for r in REPORTS if r.get("status", "active") == TTL_ACTIVE]
    return jsonify({"count": len(active), "items": active, "data_mode": "mock"})


@bp.post("/api/v1/reports")
@require_bearer_auth
def submit_report():
    """Submit a crowd-sourced report (venue-bound or GPS standalone)."""
    payload = request.get_json(silent=True) or {}

    required_fields = ["issue_type", "latitude", "longitude"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    if payload["issue_type"] not in ALLOWED_REPORT_TYPES:
        return (
            jsonify({
                "error": "Validation failed.",
                "missing_fields": [],
                "invalid_fields": ["issue_type"],
                "allowed_issue_types": sorted(ALLOWED_REPORT_TYPES),
            }),
            400,
        )

    venue_id = payload.get("venue_id")  # None => Path B standalone
    report_scope = "venue_bound" if venue_id else "standalone"
    ttl_minutes = int(payload.get("expires_in_minutes", DEFAULT_TTL_MINUTES))

    db = _db()
    if db is not None:
        try:
            with db.db_transaction() as cur:
                # FK guard: issue_type must exist + be active (db layer enforces
                # FK too, but this yields a clean 400 instead of a 500).
                if not _issue_type_exists(cur, payload["issue_type"]):
                    return (
                        jsonify({
                            "error": "Validation failed.",
                            "invalid_fields": ["issue_type"],
                            "allowed_issue_types": sorted(ALLOWED_REPORT_TYPES),
                        }),
                        400,
                    )

                report_id = str(uuid4())
                cur.execute(
                    "INSERT INTO user_reports "
                    "(report_id, user_id, venue_id, issue_type, latitude, longitude, "
                    "accuracy_meters, anonymous, description, photos, reported_by, "
                    "status, expires_in_minutes, default_language, fallback_language, "
                    "expires_at, source_confidence) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "DATE_ADD(NOW(), INTERVAL %s MINUTE), %s)",
                    (
                        report_id,
                        g.user_id,
                        venue_id,
                        payload["issue_type"],
                        payload["latitude"],
                        payload["longitude"],
                        payload.get("accuracy_m"),
                        bool(payload.get("anonymous", False)),
                        payload.get("description"),
                        _json.dumps(payload.get("photos", [])) if payload.get("photos") else None,
                        "anonymous" if payload.get("anonymous") else g.user_id,
                        TTL_ACTIVE,
                        ttl_minutes,
                        payload.get("default_language"),
                        payload.get("fallback_language"),
                        ttl_minutes,
                        0.500,
                    ),
                )

                # Re-read the inserted row for a consistent DTO.
                cur.execute(
                    "SELECT report_id, user_id, venue_id, issue_type, latitude, longitude, "
                    "accuracy_meters, anonymous, description, photos, status, created_at, "
                    "expires_at FROM user_reports WHERE report_id = %s",
                    (report_id,),
                )
                row = cur.fetchone()
            row["confirmation_count"] = 0
            row["latest_action"] = None
            row["latest_action_at"] = None
            return jsonify(_serialize_report(row)), 201
        except Exception:
            pass  # fall through to mock

    # --- Mock fallback (local dev / no DB) ---
    response = REPORT_TEMPLATE.copy()
    response["received_payload"] = payload
    response["report_id"] = _next_report_id()
    response["status"] = TTL_ACTIVE
    response["visible_in_seconds"] = 30
    response["expires_in_minutes"] = ttl_minutes
    response["report_scope"] = report_scope
    REPORTS.append({
        "report_id": response["report_id"],
        "venue_id": venue_id,
        "issue_type": payload["issue_type"],
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "status": TTL_ACTIVE,
        "confirmation_count": 0,
        "expires_in_minutes": ttl_minutes,
        "created_at": payload.get("created_at", "2026-05-28T11:00:00Z"),
        "reported_by": "anonymous",
        "badge_text": "Live report",
        "report_scope": report_scope,
    })
    response["data_mode"] = "mock"
    return jsonify(response), 201


@bp.post("/api/v1/reports/<report_id>/confirmations")
@require_bearer_auth
def confirm_report(report_id: str):
    """Confirm a report. Idempotent per (report_id, user_id)."""
    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "")

    if action not in ALLOWED_CONFIRMATION_ACTIONS:
        return (
            jsonify({
                "error": "Validation failed.",
                "missing_fields": ["action"],
                "allowed_actions": sorted(ALLOWED_CONFIRMATION_ACTIONS),
            }),
            400,
        )

    db = _db()
    if db is not None:
        try:
            with db.db_transaction() as cur:
                cur.execute(
                    "SELECT status, expires_at FROM user_reports WHERE report_id = %s",
                    (report_id,),
                )
                report = cur.fetchone()
                if not report:
                    return jsonify({"error": "Report not found."}), 404

                # Idempotent upsert honoring uq_report_user (report_id, user_id).
                cur.execute(
                    "INSERT INTO report_confirmations "
                    "(report_id, user_id, action, language, client_context) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE action = VALUES(action), "
                    "created_at = CURRENT_TIMESTAMP",
                    (
                        report_id,
                        g.user_id,
                        action,
                        payload.get("language"),
                        None,  # client_context JSON; reserved for future device/context capture
                    ),
                )

                # BE-4 action rules — only mutate ACTIVE reports.
                if action == "resolved" and report["status"] == TTL_ACTIVE:
                    cur.execute(
                        "UPDATE user_reports SET status = %s WHERE report_id = %s AND status = %s",
                        (TTL_RESOLVED, report_id, TTL_ACTIVE),
                    )
                    status = "resolved"
                elif action == "still_here" and report["status"] == TTL_ACTIVE:
                    cur.execute(
                        "UPDATE user_reports "
                        "SET expires_at = DATE_ADD(expires_at, INTERVAL %s MINUTE) "
                        "WHERE report_id = %s AND status = %s",
                        (STILL_HERE_EXTEND_MINUTES, report_id, TTL_ACTIVE),
                    )
                    status = "confirmed"
                else:
                    status = "recorded"

                # Re-read for the response DTO.
                cur.execute(
                    "SELECT ur.report_id, ur.user_id, ur.venue_id, ur.issue_type, "
                    "ur.latitude, ur.longitude, ur.accuracy_meters, ur.anonymous, "
                    "ur.description, ur.photos, ur.status, ur.created_at, ur.expires_at, "
                    "COALESCE(c.cnt, 0) AS confirmation_count, "
                    "c.latest_action, c.latest_action_at "
                    "FROM user_reports ur "
                    "LEFT JOIN ("
                    "  SELECT report_id, COUNT(*) AS cnt, "
                    "         MAX(action) AS latest_action, MAX(created_at) AS latest_action_at "
                    "  FROM report_confirmations GROUP BY report_id"
                    ") c ON c.report_id = ur.report_id "
                    "WHERE ur.report_id = %s",
                    (report_id,),
                )
                row = cur.fetchone()
            return jsonify({
                "report_id": report_id,
                "action": action,
                "status": status,
                "report": _serialize_report(row),
            })
        except Exception:
            pass  # fall through to mock

    # --- Mock fallback ---
    report = next((item for item in REPORTS if item["report_id"] == report_id), None)
    if not report:
        return jsonify({"error": "Report not found."}), 404

    if action == "still_here":
        report["confirmation_count"] = report.get("confirmation_count", 0) + 1
        report["expires_in_minutes"] = report.get("expires_in_minutes", DEFAULT_TTL_MINUTES) + STILL_HERE_EXTEND_MINUTES
        report["badge_text"] = "Multiple users confirm" if report["confirmation_count"] >= 3 else "Live report"
        response_status = "confirmed"
    elif action == "resolved":
        report["status"] = TTL_RESOLVED
        report["badge_text"] = "Resolved"
        response_status = "resolved"
    else:
        response_status = "recorded"

    return jsonify({
        "report_id": report_id,
        "action": action,
        "status": response_status,
        "report": report,
        "data_mode": "mock",
    })


# ---------------------------------------------------------------------------
# TTL cleanup (SOP 2 / BE-4) — invoked by a scheduler/worker, not a route.
# ---------------------------------------------------------------------------

def cleanup_expired_reports():
    """Soft-expire active reports whose TTL has elapsed.

    Idempotent: guarded by `status='active'` so resolved reports are never
    overwritten and re-runs are no-ops. Returns the number of rows expired.
    Designed to run on a Celery beat / scheduled job; safe to call directly.
    """
    db = _db()
    if db is None:
        return 0
    with db.db_transaction() as cur:
        cur.execute(
            "UPDATE user_reports SET status = %s "
            "WHERE status = %s AND expires_at <= NOW()",
            (TTL_EXPIRED, TTL_ACTIVE),
        )
        return cur.rowcount


# list_reports stays read-only + API-key gated (no bearer) so the public map
# can read reports without a user session; submit/confirm require a bearer
# token (user_reports.user_id is NOT NULL in the DDL).


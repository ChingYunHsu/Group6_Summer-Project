import json as _json
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from auth import require_bearer_auth, web_readonly_blocked
from mock_data import REPORTS


bp = Blueprint("reports", __name__)

# Matches the 9 category_id values seeded in 006_seed_report_categories.sql
# exactly (that file names itself the source of truth for this id<->label
# mapping — keep both in sync). Previously only had the original 6; the
# other 3 (long_waiting_time, ramp_blocked, closed_early) were seeded and
# even used by a couple of mock_data.py's REPORTS entries, but weren't
# accepted on submission and had no display label.
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

# These reports change whether an otherwise known-accessible venue can be
# used *right now*.  They are warnings, not evidence that the static OSM/NYS
# accessibility fact should be overwritten permanently.
ACCESSIBILITY_IMPACT_TYPES = {
    "elevator_broken",
    "wheelchair_lift_broken",
    "ramp_blocked",
}

DEFAULT_EXPIRES_IN_MINUTES = 120
STILL_HERE_EXTEND_MINUTES = 30


def _db():
    """Indirection point for the DB layer: tests monkeypatch this wholesale
    (including to `lambda: None`) to exercise both the DB-backed path and
    the in-memory mock fallback without needing a live MySQL."""
    try:
        import db as _db_module
    except Exception:
        return None
    return _db_module


def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else value


def _format_report(row: dict, report_scope: str | None = None) -> dict:
    return {
        "report_id": row["report_id"],
        "venue_id": row.get("venue_id"),
        "issue_type": row["issue_type"],
        "issue_type_label": ISSUE_TYPE_LABELS.get(row["issue_type"], row["issue_type"]),
        "report_scope": report_scope or ("venue_bound" if row.get("venue_id") else "standalone"),
        "status": row["status"],
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "created_at": _iso(row.get("created_at")),
        "expires_at": _iso(row.get("expires_at")),
        "confirmations": {
            "count": row.get("confirmation_count", 0),
            "latest_action": row.get("latest_action"),
            "latest_action_at": _iso(row.get("latest_action_at")),
        },
    }


def _sync_accessibility_warning(cursor, venue_id: str | None) -> None:
    """Derive a venue's transient accessibility warning from active reports."""
    if not venue_id:
        return
    placeholders = ", ".join(["%s"] * len(ACCESSIBILITY_IMPACT_TYPES))
    cursor.execute(
        "SELECT issue_type FROM user_reports WHERE venue_id = %s AND status = 'active' "
        f"AND issue_type IN ({placeholders}) ORDER BY created_at DESC LIMIT 1",
        (venue_id, *sorted(ACCESSIBILITY_IMPACT_TYPES)),
    )
    row = cursor.fetchone()
    issue_type = (
        row.get("issue_type") if isinstance(row, dict) else (row[0] if row else None)
    )
    active = bool(issue_type)
    detail = ISSUE_TYPE_LABELS.get(issue_type) if issue_type else None
    cursor.execute(
        "UPDATE venues SET active_warning = %s WHERE venue_id = %s",
        (active, venue_id),
    )
    cursor.execute(
        "INSERT INTO venue_warnings (venue_id, active_warning, warning_detail) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE active_warning = VALUES(active_warning), warning_detail = VALUES(warning_detail)",
        (venue_id, active, detail),
    )


def _submit_via_mock(payload: dict) -> dict:
    report_id = f"r_{uuid.uuid4().hex[:10]}"
    venue_id = payload.get("venue_id")
    now = datetime.now(timezone.utc)

    report = _format_report(
        {
            "report_id": report_id,
            "venue_id": venue_id,
            "issue_type": payload["issue_type"],
            "status": "active",
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "created_at": now,
            "expires_at": None,
        }
    )
    report["data_mode"] = "mock"

    try:
        # Best-effort: keep the realtime SSE stream (which drains REPORTS
        # for map_update events) seeing freshly submitted reports even when
        # there's no DB configured.
        REPORTS.append(
            {
                "report_id": report_id,
                "venue_id": venue_id,
                "issue_type": payload["issue_type"],
                "latitude": payload["latitude"],
                "longitude": payload["longitude"],
                "status": "active",
                "confirmation_count": 0,
                "created_at": now.isoformat(),
            }
        )
    except Exception:
        pass

    return report


def _submit_via_db(db_module, payload: dict) -> dict:
    report_id = f"r_{uuid.uuid4().hex[:10]}"
    venue_id = payload.get("venue_id")
    report_scope = "venue_bound" if venue_id else "standalone"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=DEFAULT_EXPIRES_IN_MINUTES)

    with db_module.db_transaction() as cursor:
        cursor.execute(
            "INSERT INTO user_reports "
            "(report_id, user_id, venue_id, issue_type, latitude, longitude, accuracy_meters, "
            " anonymous, description, photos, reported_by, status, expires_in_minutes, "
            " default_language, fallback_language, expires_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                report_id,
                g.user_id,
                venue_id,
                payload["issue_type"],
                payload["latitude"],
                payload["longitude"],
                payload.get("accuracy_meters"),
                bool(payload.get("anonymous", False)),
                payload.get("description"),
                _json.dumps(payload.get("photos", [])),
                g.user_id,
                "active",
                DEFAULT_EXPIRES_IN_MINUTES,
                payload.get("default_language", "en"),
                payload.get("fallback_language"),
                expires_at,
            
            ),
        )
        if payload["issue_type"] in ACCESSIBILITY_IMPACT_TYPES:
            _sync_accessibility_warning(cursor, venue_id)
        cursor.execute(
            "SELECT report_id, user_id, venue_id, issue_type, latitude, longitude, "
            "accuracy_meters, anonymous, description, photos, status, created_at, expires_at "
            "FROM user_reports WHERE report_id = %s",
            (report_id,),
        )
        row = cursor.fetchone()

    return _format_report(row, report_scope) | {"data_mode": "db"}


@bp.post("/api/v1/reports")
@require_bearer_auth
def submit_report():
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

    payload = request.get_json(silent=True) or {}

    if "issue_type" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["issue_type"]}), 400

    missing = [field for field in ("latitude", "longitude") if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    if payload["issue_type"] not in ALLOWED_REPORT_TYPES:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": [],
                    "invalid_fields": ["issue_type"],
                    "allowed_issue_types": sorted(ALLOWED_REPORT_TYPES),
                }
            ),
            400,
        )

    db_module = _db()
    if db_module is None:
        return jsonify(_submit_via_mock(payload)), 201

    try:
        return jsonify(_submit_via_db(db_module, payload)), 201
    except Exception:
        return jsonify(_submit_via_mock(payload)), 201


@bp.get("/api/v1/reports")
def list_reports():
    db_module = _db()
    if db_module is not None:
        try:
            with db_module.db_cursor() as cursor:
                cursor.execute(
                    "SELECT ur.report_id, ur.user_id, ur.venue_id, ur.issue_type, "
                    "ur.latitude, ur.longitude, ur.status, ur.created_at, ur.expires_at, "
                    "COUNT(rc.report_id) AS confirmation_count "
                    "FROM user_reports ur "
                    "LEFT JOIN report_confirmations rc ON rc.report_id = ur.report_id "
                    "WHERE ur.status = %s "
                    "GROUP BY ur.report_id",
                    ("active",),
                )
                rows = cursor.fetchall()
            return jsonify(
                {
                    "data_mode": "db",
                    "count": len(rows),
                    "items": [_format_report(row) for row in rows],
                }
            )
        except Exception:
            pass  # Fallback to mock data below.

    # Route the mock fallback through the same _format_report() shape as the
    # DB path, rather than returning REPORTS' raw (richer) mock shape — the
    # contract must not change depending on whether MySQL happens to be up.
    items = [_flatten_mock_report_confirmations(report) for report in REPORTS]
    return jsonify(
        {
            "data_mode": "mock",
            "count": len(items),
            "items": [_format_report(item) for item in items],
        }
    )


def _flatten_mock_report_confirmations(report: dict) -> dict:
    confirmations = report.get("confirmations") or {}
    return {
        **report,
        "confirmation_count": confirmations.get("count", report.get("confirmation_count", 0)),
        "latest_action": confirmations.get("latest_action"),
        "latest_action_at": confirmations.get("latest_action_at"),
    }


@bp.post("/api/v1/reports/<report_id>/confirmations")
@require_bearer_auth
def confirm_report(report_id: str):
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "")

    if action not in ALLOWED_CONFIRMATION_ACTIONS:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": ["action"],
                    "allowed_actions": sorted(ALLOWED_CONFIRMATION_ACTIONS),
                }
            ),
            400,
        )

    db_module = _db()
    if db_module is None:
        return jsonify({"error": "Report not found."}), 404

    try:
        with db_module.db_transaction() as cursor:
            cursor.execute(
                "SELECT venue_id, issue_type, status, expires_at FROM user_reports WHERE report_id = %s",
                (report_id,),
            )
            current = cursor.fetchone()
            if not current:
                return jsonify({"error": "Report not found."}), 404

            cursor.execute(
                "INSERT INTO report_confirmations (report_id, user_id, action, language, client_context) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE action = VALUES(action), created_at = NOW()",
                (report_id, g.user_id, action, payload.get("language"), payload.get("context")),
            )

            if action == "resolved":
                cursor.execute(
                    "UPDATE user_reports SET status = %s WHERE report_id = %s AND status = %s",
                    ("resolved", report_id, current["status"]),
                )
                response_status = "resolved"
            elif action == "still_here":
                cursor.execute(
                    "UPDATE user_reports SET expires_at = DATE_ADD(expires_at, INTERVAL %s MINUTE) "
                    "WHERE report_id = %s AND status = %s",
                    (STILL_HERE_EXTEND_MINUTES, report_id, current["status"]),
                )
                response_status = "confirmed"
            else:
                response_status = "recorded"

            if current["issue_type"] in ACCESSIBILITY_IMPACT_TYPES:
                _sync_accessibility_warning(cursor, current["venue_id"])

            cursor.execute(
                "SELECT ur.report_id, ur.user_id, ur.venue_id, ur.issue_type, ur.latitude, "
                "ur.longitude, ur.status, ur.created_at, ur.expires_at "
                "FROM user_reports ur WHERE ur.report_id = %s",
                (report_id,),
            )
            updated = cursor.fetchone()
    except Exception:
        return jsonify({"error": "Report not found."}), 404

    return jsonify(
        {
            "report_id": report_id,
            "action": action,
            "status": response_status,
            "report": _format_report(updated) if updated else None,
        }
    )


def cleanup_expired_reports() -> int:
    """Soft-expire active reports whose expires_at has passed. Safe to call
    repeatedly (idempotent) — a report already flipped to "expired" no
    longer matches status = 'active' so a second run touches 0 rows."""
    db_module = _db()
    if db_module is None:
        return 0

    with db_module.db_transaction() as cursor:
        cursor.execute(
            "UPDATE user_reports SET status = %s WHERE status = %s AND expires_at <= NOW()",
            ("expired", "active"),
        )
        return cursor.rowcount

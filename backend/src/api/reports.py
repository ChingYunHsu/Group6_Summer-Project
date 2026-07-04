from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from db import db_transaction
from mock_data import REPORT_TEMPLATE, REPORTS


bp = Blueprint("reports", __name__)

ALLOWED_REPORT_TYPES = {
    "elevator_broken",
    "wheelchair_lift_broken",
    "toilet_out_of_order",
    "large_crowd",
    "protest_or_blockage",
    "entrance_closed",
}

ALLOWED_CONFIRMATION_ACTIONS = {
    "still_here",
    "resolved",
    "not_sure",
    "still_out_of_order",
    "open_now",
}


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


@bp.get("/api/v1/reports")
def list_reports():
    return jsonify({"count": len(REPORTS), "items": REPORTS})


def _resolve_report_path(payload: dict):
    """Classify the wizard submission as Path A (Venue Bound — a `venue_id`
    was supplied, coordinates optional/derived from the venue) or Path B
    (Pure GPS Standalone — no venue, coordinates come straight from the
    device). Returns (report_path, error_response) where error_response is
    None on success."""
    venue_id = payload.get("venue_id")

    if venue_id:
        return "venue_bound", None

    if "latitude" not in payload or "longitude" not in payload:
        return None, (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": ["venue_id (Path A) or latitude/longitude (Path B)"],
                }
            ),
            400,
        )

    return "gps_standalone", None


def _persist_report(report: dict, report_path: str) -> None:
    """Best-effort write-through to the user_reports table. Swallows DB
    errors so the in-memory REPORTS list (used for reads today) stays the
    source of truth even when MySQL is unreachable, matching the fallback
    convention used elsewhere in this API (see api/venues.py)."""
    try:
        with db_transaction() as cursor:
            cursor.execute(
                "INSERT INTO user_reports "
                "(report_id, report_path, venue_id, issue_type, latitude, longitude, "
                " status, confirmation_count, upvote_count, reported_by, latest_action_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    report["report_id"],
                    report_path,
                    report["venue_id"],
                    report["issue_type"],
                    report["latitude"],
                    report["longitude"],
                    report["status"],
                    report["confirmation_count"],
                    0,
                    report["reported_by"],
                    datetime.now(timezone.utc),
                ),
            )
    except Exception:
        pass  # In-memory REPORTS list remains the source of truth for reads.


@bp.post("/api/v1/reports")
def submit_report():
    payload = request.get_json(silent=True) or {}

    if "issue_type" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["issue_type"]}), 400

    report_path, error_response = _resolve_report_path(payload)
    if error_response:
        return error_response

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

    response = REPORT_TEMPLATE.copy()
    response["received_payload"] = payload
    response["report_id"] = _next_report_id()
    response["report_path"] = report_path
    response["status"] = "active"
    response["visible_in_seconds"] = 30
    response["expires_in_minutes"] = 120

    report = {
        "report_id": response["report_id"],
        "report_path": report_path,
        "venue_id": payload.get("venue_id"),
        "issue_type": payload["issue_type"],
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "status": "active",
        "confirmation_count": 0,
        "expires_in_minutes": 120,
        "created_at": payload.get("created_at", "2026-05-28T11:00:00Z"),
        "reported_by": "anonymous",
        "badge_text": "Live report",
    }
    REPORTS.append(report)
    _persist_report(report, report_path)

    return jsonify(response), 201


def _persist_confirmation(report_id: str, action: str, report: dict) -> None:
    """Best-effort write-through of the confirmation event and the report's
    updated counters/status, mirroring the fallback convention in
    _persist_report — DB errors never block the in-memory response."""
    try:
        with db_transaction() as cursor:
            cursor.execute(
                "INSERT INTO report_confirmations (report_id, action) VALUES (%s, %s)",
                (report_id, action),
            )
            cursor.execute(
                "UPDATE user_reports SET status = %s, confirmation_count = %s, "
                "latest_action_at = %s WHERE report_id = %s",
                (report["status"], report["confirmation_count"], datetime.now(timezone.utc), report_id),
            )
    except Exception:
        pass


@bp.post("/api/v1/reports/<report_id>/confirmations")
def confirm_report(report_id: str):
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

    report = next((item for item in REPORTS if item["report_id"] == report_id), None)
    if not report:
        return jsonify({"error": "Report not found."}), 404

    if action == "still_here":
        report["confirmation_count"] += 1
        report["expires_in_minutes"] += 30
        report["badge_text"] = "Multiple users confirm" if report["confirmation_count"] >= 3 else "Live report"
        response_status = "confirmed"
    elif action == "resolved":
        report["status"] = "resolved"
        report["badge_text"] = "Resolved"
        response_status = "resolved"
    else:
        response_status = "recorded"

    _persist_confirmation(report_id, action, report)

    return jsonify({"report_id": report_id, "action": action, "status": response_status, "report": report})

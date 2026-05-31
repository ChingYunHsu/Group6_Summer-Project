from flask import Blueprint, jsonify, request

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


@bp.post("/api/v1/reports")
def submit_report():
    payload = request.get_json(silent=True) or {}

    required_fields = ["issue_type", "latitude", "longitude"]
    missing = [field for field in required_fields if field not in payload]
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

    response = REPORT_TEMPLATE.copy()
    response["received_payload"] = payload
    response["report_id"] = _next_report_id()
    response["status"] = "active"
    response["visible_in_seconds"] = 30
    response["expires_in_minutes"] = 120

    REPORTS.append(
        {
            "report_id": response["report_id"],
            "venue_id": payload.get("venue_id"),
            "issue_type": payload["issue_type"],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "status": "active",
            "confirmation_count": 0,
            "expires_in_minutes": 120,
            "created_at": payload.get("created_at", "2026-05-28T11:00:00Z"),
            "reported_by": "anonymous",
            "badge_text": "Live report",
        }
    )
    return jsonify(response), 201


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

    return jsonify({"report_id": report_id, "action": action, "status": response_status, "report": report})
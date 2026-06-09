from flask import Blueprint, jsonify, request

from mock_data import INSIGHTS_DASHBOARD


bp = Blueprint("insights", __name__)


@bp.get("/api/v1/insights")
def get_insights():
    district = request.args.get("district") or INSIGHTS_DASHBOARD.get("district", "all")
    dashboard = INSIGHTS_DASHBOARD.copy()

    response = {
        "district": district,
        "real_time_density": {
            "percent": dashboard["real_time_density"]["percent"],
            "trend": dashboard["real_time_density"].get("trend_label", dashboard["real_time_density"].get("trend", "")),
            "trend_label": dashboard["real_time_density"].get("trend_label"),
        },
        "quick_triage": {
            "wait_minutes": dashboard["quick_triage"]["wait_minutes"],
            "label": dashboard["quick_triage"].get("venue_name", dashboard["quick_triage"].get("label", "")),
            "venue_name": dashboard["quick_triage"].get("venue_name"),
        },
        "best_travel_window": {
            "start_time": dashboard["best_travel_window"].get("start_time", dashboard["best_travel_window"].get("start", "")),
            "end_time": dashboard["best_travel_window"].get("end_time", dashboard["best_travel_window"].get("end", "")),
            "start": dashboard["best_travel_window"].get("start"),
            "end": dashboard["best_travel_window"].get("end"),
            "cta_label": dashboard["best_travel_window"].get("cta_label"),
        },
        "chart_mode": dashboard.get("chart_mode"),
        "prediction_series": dashboard.get("prediction_series", []),
        "history_series_7d": dashboard.get("history_series_7d", []),
        "fastest_hubs": [
            {
                "rank": hub.get("rank"),
                "venue_id": hub.get("venue_id"),
                "clinic_name": hub.get("venue_name"),
                "venue_name": hub.get("venue_name"),
                "capacity_label": hub.get("flow_status"),
                "flow_status": hub.get("flow_status"),
                "travel_minutes": hub.get("travel_minutes"),
                "wait_minutes": hub.get("wait_minutes"),
                "languages": hub.get("language_flags", []),
                "language_flags": hub.get("language_flags", []),
            }
            for hub in dashboard.get("fastest_hubs", [])
        ],
    }

    return jsonify(response)

from flask import Blueprint, jsonify, request

from auth import require_api_key
from mock_data import VENUES


bp = Blueprint("venues", __name__)


@bp.get("/api/v1/venues")
@require_api_key
def list_venues():
    languages_param = request.args.get("languages", "")
    accessible_param = request.args.get("accessible", "")
    open_now_param = request.args.get("open_now", "")

    selected_languages = [language.strip().upper() for language in languages_param.split(",") if language.strip()]
    accessible_filter = accessible_param.lower() if accessible_param else ""
    open_now_filter = open_now_param.lower() if open_now_param else ""

    filtered_items = VENUES

    if selected_languages:
        filtered_items = [
            venue for venue in filtered_items if any(language in venue["language_tags"] for language in selected_languages)
        ]

    if accessible_filter in {"true", "false"}:
        if accessible_filter == "true":
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] == "full_access"]
        else:
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] != "full_access"]

    if open_now_filter in {"true", "false"}:
        expected_open = open_now_filter == "true"
        filtered_items = [venue for venue in filtered_items if venue["open_now"] == expected_open]

    return jsonify({"count": len(filtered_items), "items": filtered_items})


@bp.get("/api/v1/venues/<venue_id>")
@require_api_key
def get_venue(venue_id: str):
    venue = next((venue for venue in VENUES if venue["venue_id"] == venue_id), None)
    if not venue:
        return jsonify({"error": "Venue not found."}), 404
    return jsonify(venue)
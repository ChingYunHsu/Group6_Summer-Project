from copy import deepcopy

from flask import Blueprint, jsonify, request

from auth import require_api_key, web_readonly_blocked
from mock_data import (
    DELETE_ACCOUNT_RESPONSE,
    FAVOURITE_CREATE_TEMPLATE,
    FAVOURITES,
    LANGUAGE_OPTIONS,
    MEDICAL_PASSPORT_RESPONSE,
    NOTIFICATION_PREFERENCES,
    SOS_RESPONSE,
    USER_PROFILE,
    USER_SETTINGS,
)


bp = Blueprint("user", __name__)

# Registration-locked fields (user_id, email, full_name) are intentionally
# excluded — they cannot be edited via this endpoint.
PROFILE_EDITABLE_FIELDS = {"phone", "nationality", "spoken_languages"}

SETTINGS_EDITABLE_FIELDS = {
    "selected_language",
    "selected_language_native",
    "location_access_enabled",
    "notifications_enabled",
    "privacy_mode",
    "guest_mode_enabled",
    "show_medical_id_on_sos",
}

NOTIFICATION_PREFERENCES_EDITABLE_FIELDS = {
    "busyness_alerts_enabled",
    "push_notifications_enabled",
    "quiet_hours_enabled",
    "quiet_hours_start",
    "quiet_hours_end",
    "alert_threshold_percent",
    "preferred_venue_types",
    "preferred_boroughs",
}

SOS_FIELDS = {"latitude", "longitude", "share_live_location", "note"}


@bp.get("/api/v1/user/profile")
@require_api_key
def get_user_profile():
    return jsonify(deepcopy(USER_PROFILE))


@bp.put("/api/v1/user/profile")
@require_api_key
def update_user_profile():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in PROFILE_EDITABLE_FIELDS]
    if invalid_fields:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": [],
                    "invalid_fields": invalid_fields,
                }
            ),
            400,
        )

    for field in PROFILE_EDITABLE_FIELDS:
        if field in payload:
            USER_PROFILE[field] = payload[field]

    return jsonify(deepcopy(USER_PROFILE))


@bp.get("/api/v1/user/settings")
@require_api_key
def get_user_settings():
    return jsonify(deepcopy(USER_SETTINGS))


@bp.put("/api/v1/user/settings")
@require_api_key
def update_user_settings():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in SETTINGS_EDITABLE_FIELDS]
    if invalid_fields:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": [],
                    "invalid_fields": invalid_fields,
                }
            ),
            400,
        )

    for field in SETTINGS_EDITABLE_FIELDS:
        if field in payload:
            USER_SETTINGS[field] = payload[field]

    return jsonify(deepcopy(USER_SETTINGS))


@bp.get("/api/v1/user/languages")
@require_api_key
def get_language_options():
    return jsonify({"count": len(LANGUAGE_OPTIONS), "items": deepcopy(LANGUAGE_OPTIONS)})


@bp.get("/api/v1/user/favourites")
@require_api_key
def get_favourites():
    return jsonify({"count": len(FAVOURITES), "items": deepcopy(FAVOURITES)})


@bp.post("/api/v1/user/favourites")
@require_api_key
def add_favourite():
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

    payload = request.get_json(silent=True) or {}

    if "venue_id" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["venue_id"]}), 400

    favourite = deepcopy(FAVOURITE_CREATE_TEMPLATE)
    favourite["venue_id"] = payload["venue_id"]
    FAVOURITES.append(favourite)

    return jsonify(favourite), 201


@bp.delete("/api/v1/user/favourites/<venue_id>")
@require_api_key
def delete_favourite(venue_id: str):
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

    favourite = next((item for item in FAVOURITES if item["venue_id"] == venue_id), None)
    if not favourite:
        return jsonify({"error": "Favourite not found."}), 404

    FAVOURITES.remove(favourite)
    return "", 204


@bp.get("/api/v1/user/notification-preferences")
@require_api_key
def get_notification_preferences():
    return jsonify(deepcopy(NOTIFICATION_PREFERENCES))


@bp.put("/api/v1/user/notification-preferences")
@require_api_key
def update_notification_preferences():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in NOTIFICATION_PREFERENCES_EDITABLE_FIELDS]
    if invalid_fields:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": [],
                    "invalid_fields": invalid_fields,
                }
            ),
            400,
        )

    for field in NOTIFICATION_PREFERENCES_EDITABLE_FIELDS:
        if field in payload:
            NOTIFICATION_PREFERENCES[field] = payload[field]

    return jsonify(deepcopy(NOTIFICATION_PREFERENCES))


@bp.post("/api/v1/user/sos")
@require_api_key
def trigger_sos():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in SOS_FIELDS]
    if invalid_fields:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": [],
                    "invalid_fields": invalid_fields,
                }
            ),
            400,
        )

    return jsonify(deepcopy(SOS_RESPONSE))


@bp.delete("/api/v1/user/account")
@require_api_key
def delete_account():
    return jsonify(deepcopy(DELETE_ACCOUNT_RESPONSE))


@bp.get("/api/v1/user/medical-passport")
@require_api_key
def get_medical_passport():
    response = deepcopy(MEDICAL_PASSPORT_RESPONSE)

    language = request.args.get("language")
    if language:
        response["language"] = language

    return jsonify(response)

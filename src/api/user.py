from copy import deepcopy

from flask import Blueprint, jsonify, request

from auth import require_api_key
from mock_data import (
    FAVOURITES,
    LANGUAGE_OPTIONS,
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

from copy import deepcopy

from flask import Blueprint, jsonify, request

from auth import require_api_key, require_bearer_auth
from mock_data import (
    EMERGENCY_CONTACT_CREATE_TEMPLATE,
    EMERGENCY_CONTACTS,
    FAVOURITES,
    LANGUAGE_OPTIONS,
    MEDICAL_PASSPORT_RESPONSE,
    NOTIFICATION_PREFERENCES,
    SOS_RESPONSE,
    USER_PROFILE,
    USER_SETTINGS,
)


bp = Blueprint("user", __name__)

MEDICAL_ID_EDITABLE_FIELDS = {"blood_type", "conditions", "allergies"}

EMERGENCY_CONTACT_EDITABLE_FIELDS = {"name", "relationship", "phone"}


def _next_contact_id() -> str:
    contact_numbers = []
    for contact in EMERGENCY_CONTACTS:
        contact_id = contact.get("contact_id", "")
        if contact_id.startswith("ec_"):
            try:
                contact_numbers.append(int(contact_id.removeprefix("ec_")))
            except ValueError:
                continue

    next_number = max(contact_numbers, default=0) + 1
    return f"ec_{next_number:03d}"


@bp.get("/api/v1/user/profile")
@require_bearer_auth
def get_user_profile():
    return jsonify(deepcopy(USER_PROFILE))


@bp.get("/api/v1/user/medical-id")
@require_bearer_auth
def get_medical_id():
    return jsonify(deepcopy(MEDICAL_ID))


@bp.put("/api/v1/user/medical-id")
@require_bearer_auth
def update_medical_id():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in MEDICAL_ID_EDITABLE_FIELDS]
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

    for field in MEDICAL_ID_EDITABLE_FIELDS:
        if field in payload:
            MEDICAL_ID[field] = payload[field]

    return jsonify(deepcopy(MEDICAL_ID))


@bp.get("/api/v1/user/emergency-contacts")
@require_bearer_auth
def get_emergency_contacts():
    return jsonify({"count": len(EMERGENCY_CONTACTS), "items": deepcopy(EMERGENCY_CONTACTS)})
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


@bp.post("/api/v1/user/emergency-contacts")
@require_bearer_auth
def add_emergency_contact():
    payload = request.get_json(silent=True) or {}

    missing = [field for field in EMERGENCY_CONTACT_EDITABLE_FIELDS if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    contact = deepcopy(EMERGENCY_CONTACT_CREATE_TEMPLATE)
    contact["contact_id"] = _next_contact_id()
    for field in EMERGENCY_CONTACT_EDITABLE_FIELDS:
        contact[field] = payload[field]
    EMERGENCY_CONTACTS.append(contact)

    return jsonify(contact), 201


@bp.put("/api/v1/user/emergency-contacts/<contact_id>")
@require_bearer_auth
def update_emergency_contact(contact_id: str):
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in EMERGENCY_CONTACT_EDITABLE_FIELDS]
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

    contact = next((item for item in EMERGENCY_CONTACTS if item["contact_id"] == contact_id), None)
    if not contact:
        return jsonify({"error": "Emergency contact not found."}), 404

    for field in EMERGENCY_CONTACT_EDITABLE_FIELDS:
        if field in payload:
            contact[field] = payload[field]

    return jsonify(deepcopy(contact))


@bp.delete("/api/v1/user/emergency-contacts/<contact_id>")
@require_bearer_auth
def delete_emergency_contact(contact_id: str):
    contact = next((item for item in EMERGENCY_CONTACTS if item["contact_id"] == contact_id), None)
    if not contact:
        return jsonify({"error": "Emergency contact not found."}), 404

    EMERGENCY_CONTACTS.remove(contact)
    return "", 204


@bp.get("/api/v1/user/settings")
@require_bearer_auth
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

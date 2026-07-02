from copy import deepcopy
import json
from flask import Blueprint, g, jsonify, request

import db
import medical_crypto
from flask import Blueprint, g, jsonify, request

import db
from auth import require_api_key, require_bearer_auth, web_readonly_blocked
from mock_data import (
    DELETE_ACCOUNT_RESPONSE,
    EMERGENCY_CONTACT_CREATE_TEMPLATE,
    EMERGENCY_CONTACTS,
    FAVOURITE_CREATE_TEMPLATE,
    FAVOURITES,
    LANGUAGE_OPTIONS,
    MEDICAL_ID,
    MEDICAL_PASSPORT_RESPONSE,
    NOTIFICATION_PREFERENCES,
    SOS_RESPONSE,
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

MEDICAL_ID_EDITABLE_FIELDS = {"blood_type", "conditions", "allergies"}

EMERGENCY_CONTACT_EDITABLE_FIELDS = {"name", "relationship", "phone"}

MEDICAL_PROFILE_EDITABLE_FIELDS = {"blood_type", "conditions", "allergies"}

MEDICAL_PROFILE_DEFAULTS = {"blood_type": None, "conditions": [], "allergies": []}

NOTIFICATION_PREFERENCES_DEFAULTS = {
    "busyness_alerts_enabled": True,
    "push_notifications_enabled": True,
    "quiet_hours_enabled": False,
    "quiet_hours_start": None,
    "quiet_hours_end": None,
    "alert_threshold_percent": 80,
    "preferred_venue_types": [],
    "preferred_boroughs": [],
}


def _reject_explicit_user_id():
    """Strict isolation: identity comes only from the Bearer token's sub
    claim. Callers must never be able to address another user's profile by
    passing user_id explicitly."""
    if "user_id" in request.args:
        return (
            jsonify(
                {
                    "error": "Forbidden. user_id may not be supplied explicitly; "
                    "identity is resolved from the access token.",
                }
            ),
            400,
        )
    return None


def _reject_explicit_user_id():
    """Strict isolation: identity comes only from the Bearer token's sub
    claim. Callers must never be able to address another user's profile by
    passing user_id explicitly."""
    if "user_id" in request.args:
        return (
            jsonify(
                {
                    "error": "Forbidden. user_id may not be supplied explicitly; "
                    "identity is resolved from the access token.",
                }
            ),
            400,
        )
    return None


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

    with db.db_cursor() as cursor:
        cursor.execute("SELECT display_name, phone, nationality, spoken_languages FROM users WHERE user_id = %s", (g.user_id,))
        row = cursor.fetchone()

    return jsonify(row)


    


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


@bp.get("/api/v1/user/medical-profile")
@require_bearer_auth
def get_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    with db.db_cursor() as cursor:
        cursor.execute(
            "SELECT encrypted_payload FROM medical_profiles WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    if not row:
        return jsonify(deepcopy(MEDICAL_PROFILE_DEFAULTS))

    return jsonify(medical_crypto.decrypt_profile(row["encrypted_payload"]))


@bp.put("/api/v1/user/medical-profile")
@require_bearer_auth
def upsert_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    payload = request.get_json(silent=True) or {}
    invalid_fields = [field for field in payload if field not in MEDICAL_PROFILE_EDITABLE_FIELDS]
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

    with db.db_transaction() as cursor:
        cursor.execute(
            "SELECT encrypted_payload FROM medical_profiles WHERE user_id = %s FOR UPDATE",
            (g.user_id,),
        )
        row = cursor.fetchone()
        profile = (
            medical_crypto.decrypt_profile(row["encrypted_payload"])
            if row
            else deepcopy(MEDICAL_PROFILE_DEFAULTS)
        )

        for field in MEDICAL_PROFILE_EDITABLE_FIELDS:
            if field in payload:
                profile[field] = payload[field]

        encrypted_payload = medical_crypto.encrypt_profile(profile)
        cursor.execute(
            "INSERT INTO medical_profiles (user_id, encrypted_payload) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE encrypted_payload = %s",
            (g.user_id, encrypted_payload, encrypted_payload),
        )

    return jsonify(profile)


@bp.delete("/api/v1/user/medical-profile")
@require_bearer_auth
def delete_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    with db.db_transaction() as cursor:
        cursor.execute("DELETE FROM medical_profiles WHERE user_id = %s", (g.user_id,))

    return "", 204


@bp.get("/api/v1/user/emergency-contacts")
@require_bearer_auth
def get_emergency_contacts():
    return jsonify({"count": len(EMERGENCY_CONTACTS), "items": deepcopy(EMERGENCY_CONTACTS)})


@bp.put("/api/v1/user/profile")
@require_bearer_auth
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
    
    fields_to_update = [field for field in PROFILE_EDITABLE_FIELDS if field in payload]

    with db.db_transaction() as cursor:
        if fields_to_update:
            set_clause = ", ".join(f"{field} = %s" for field in fields_to_update)
            values = [payload[field] for field in fields_to_update] + [g.user_id]
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s", values)

        cursor.execute(
            "SELECT display_name, phone, nationality, spoken_languages FROM users WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    return jsonify(row)



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
@require_bearer_auth
def get_notification_preferences():

    with db.db_cursor() as cursor:
        cursor.execute(
            "SELECT notification_preferences FROM users WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

        if not row:
            return jsonify(deepcopy(NOTIFICATION_PREFERENCES_DEFAULTS))

    return jsonify(json.loads(row["notification_preferences"]))


@bp.put("/api/v1/user/notification-preferences")
@require_bearer_auth
def update_notification_preferences():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in NOTIFICATION_PREFERENCES_EDITABLE_FIELDS]
    if invalid_fields:
        return jsonify({
            "error": "Validation failed.",
            "missing_fields": [],
            "invalid_fields": invalid_fields,
        }), 400

    with db.db_transaction() as cursor:
        cursor.execute(
            "SELECT notification_preferences FROM users WHERE user_id = %s FOR UPDATE",
            (g.user_id,),
        )
        row = cursor.fetchone()
        preferences = json.loads(row["notification_preferences"]) if row else {}
        preferences.update({k: v for k, v in payload.items() if k in NOTIFICATION_PREFERENCES_EDITABLE_FIELDS})

        cursor.execute(
            "UPDATE users SET notification_preferences = %s WHERE user_id = %s",
            (json.dumps(preferences), g.user_id),
        )

    return jsonify(preferences)



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

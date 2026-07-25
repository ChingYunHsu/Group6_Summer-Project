from copy import deepcopy
import json
import uuid
from datetime import datetime, timezone

import pymysql
from flask import Blueprint, g, jsonify, request

import db
from sos_buffer import push_sos_event
from auth import require_api_key, require_bearer_auth
from mock_data import (
    DELETE_ACCOUNT_RESPONSE,
    EMERGENCY_CONTACT_CREATE_TEMPLATE,
    EMERGENCY_CONTACTS,
    LANGUAGE_OPTIONS,
    MEDICAL_ID,
    MEDICAL_PASSPORT_RESPONSE,
    NOTIFICATION_PREFERENCES,
    SOS_RESPONSE,
    USER_SETTINGS,
)

_BUSYNESS_LEVEL_TO_DISPLAY_STATUS = {
    "quiet": "OPTIMAL FLOW",
    "moderate": "MODERATE",
    "busy": "DIVERTING",
}

# Settings' `selected_language` (system UI language) and Profile's
# `spoken_languages` (medical/communication languages, e.g. for the bilingual
# Medical Passport) are deliberately separate per-user DB columns on `users`
# — preferred_language vs spoken_languages. These maps translate between the
# language codes used across the API (LANGUAGE_OPTIONS/chatbot ui_language)
# and the full English names stored in spoken_languages.
_LANGUAGE_CODE_TO_NATIVE_NAME = {option["code"]: option["native_name"] for option in LANGUAGE_OPTIONS}
_ENGLISH_NAME_TO_LANGUAGE_CODE = {option["english_name"].lower(): option["code"] for option in LANGUAGE_OPTIONS}


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

SOS_FIELDS = {"latitude", "longitude", "tracking_metrics", "share_live_location", "note"}

MEDICAL_ID_EDITABLE_FIELDS = {"blood_type", "conditions", "allergies"}

EMERGENCY_CONTACT_EDITABLE_FIELDS = {"name", "relationship", "phone"}

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


def _parse_spoken_languages(raw_languages) -> list:
    if isinstance(raw_languages, str):
        return json.loads(raw_languages)
    return raw_languages or []


def _second_spoken_language_code(spoken_languages: list) -> str | None:
    """First spoken language that isn't English, as an API language code.
    English is always the Medical Passport's common/primary language, so it
    never counts as the "second" one."""
    for language in spoken_languages:
        if not isinstance(language, str):
            continue
        normalised = language.strip()
        if not normalised or normalised.lower() == "english":
            continue
        return _ENGLISH_NAME_TO_LANGUAGE_CODE.get(normalised.lower(), normalised)
    return None


def _format_profile(row: dict) -> dict:
    spoken_languages = _parse_spoken_languages(row["spoken_languages"])

    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "full_name": row["display_name"],
        "phone": row["phone"],
        "nationality": row["nationality"],
        "spoken_languages": spoken_languages,
    }


@bp.get("/api/v1/user/profile")
@require_bearer_auth
def get_user_profile():
    with db.db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id, email, display_name, phone, nationality, spoken_languages "
            "FROM users WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    if not row:
        return jsonify({"error": "User not found."}), 404

    return jsonify(_format_profile(row))


    


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
            values = [json.dumps(payload[field]) if field == "spoken_languages" else payload[field] for field in fields_to_update] + [g.user_id]
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s", values)

        cursor.execute(
            "SELECT user_id, email, display_name, phone, nationality, spoken_languages "
            "FROM users WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    return jsonify(_format_profile(row))



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


def _language_settings_for_user(user_id: str) -> dict:
    """selected_language is per-user and DB-backed (users.preferred_language)
    — deliberately separate from Profile's spoken_languages, which drives
    the Medical Passport instead. selected_language_native is always derived
    from the code; it is never stored independently."""
    with db.db_cursor() as cursor:
        cursor.execute("SELECT preferred_language FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()

    code = (row["preferred_language"] if row else None) or "en"
    return {
        "selected_language": code,
        "selected_language_native": _LANGUAGE_CODE_TO_NATIVE_NAME.get(code, code),
    }


@bp.get("/api/v1/user/settings")
@require_bearer_auth
def get_user_settings():
    settings = deepcopy(USER_SETTINGS)
    settings.update(_language_settings_for_user(g.user_id))
    return jsonify(settings)


@bp.put("/api/v1/user/settings")
@require_bearer_auth
def update_user_settings():
    payload = request.get_json(silent=True) or {}

    invalid_fields = [field for field in payload if field not in SETTINGS_EDITABLE_FIELDS]
    if "selected_language" in payload and payload["selected_language"] not in _LANGUAGE_CODE_TO_NATIVE_NAME:
        invalid_fields.append("selected_language")
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

    if "selected_language" in payload:
        with db.db_transaction() as cursor:
            cursor.execute(
                "UPDATE users SET preferred_language = %s WHERE user_id = %s",
                (payload["selected_language"], g.user_id),
            )

    # selected_language_native is derived, never stored — ignored here even
    # if the client sends one alongside selected_language.
    for field in SETTINGS_EDITABLE_FIELDS - {"selected_language", "selected_language_native"}:
        if field in payload:
            USER_SETTINGS[field] = payload[field]

    settings = deepcopy(USER_SETTINGS)
    settings.update(_language_settings_for_user(g.user_id))
    return jsonify(settings)


@bp.get("/api/v1/user/languages")
@require_api_key
def get_language_options():
    return jsonify({"count": len(LANGUAGE_OPTIONS), "items": deepcopy(LANGUAGE_OPTIONS)})


def _favourite_id(venue_id: str) -> str:
    return f"fav_{venue_id}"


def _format_favourite(row: dict) -> dict:
    return {
        "favourite_id": _favourite_id(row["venue_id"]),
        "venue_id": row["venue_id"],
        "saved_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "display_status": _BUSYNESS_LEVEL_TO_DISPLAY_STATUS.get(row.get("level"), "NO DATA"),
    }


@bp.get("/api/v1/user/favourites")
@require_bearer_auth
def get_favourites():
    with db.db_cursor() as cursor:
        cursor.execute(
            "SELECT ufv.venue_id, ufv.created_at, "
            "(SELECT bs.level FROM busyness_scores bs WHERE bs.venue_id = ufv.venue_id "
            " ORDER BY bs.created_at DESC LIMIT 1) AS level "
            "FROM user_favorite_venues ufv "
            "WHERE ufv.user_id = %s "
            "ORDER BY ufv.created_at DESC",
            (g.user_id,),
        )
        rows = cursor.fetchall()

    items = [_format_favourite(row) for row in rows]
    return jsonify({"count": len(items), "items": items})


@bp.post("/api/v1/user/favourites")
@require_bearer_auth
def add_favourite():
    payload = request.get_json(silent=True) or {}

    if "venue_id" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["venue_id"]}), 400

    venue_id = payload["venue_id"]

    try:
        with db.db_transaction() as cursor:
            # Idempotent: favouriting an already-favourited venue succeeds
            # rather than raising on the (user_id, venue_id) primary key.
            cursor.execute(
                "INSERT INTO user_favorite_venues (user_id, venue_id) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE venue_id = venue_id",
                (g.user_id, venue_id),
            )
            cursor.execute(
                "SELECT ufv.venue_id, ufv.created_at, "
                "(SELECT bs.level FROM busyness_scores bs WHERE bs.venue_id = ufv.venue_id "
                " ORDER BY bs.created_at DESC LIMIT 1) AS level "
                "FROM user_favorite_venues ufv WHERE ufv.user_id = %s AND ufv.venue_id = %s",
                (g.user_id, venue_id),
            )
            row = cursor.fetchone()
    except pymysql.err.IntegrityError:
        return jsonify({"error": "Validation failed.", "invalid_fields": ["venue_id"]}), 400

    return jsonify(_format_favourite(row)), 201


@bp.delete("/api/v1/user/favourites/<venue_id>")
@require_bearer_auth
def delete_favourite(venue_id: str):
    with db.db_transaction() as cursor:
        cursor.execute(
            "DELETE FROM user_favorite_venues WHERE user_id = %s AND venue_id = %s",
            (g.user_id, venue_id),
        )
        deleted = cursor.rowcount

    if not deleted:
        return jsonify({"error": "Favourite not found."}), 404

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

    incident_id = f"sos_{uuid.uuid4().hex[:8]}"
    # High-priority/low-latency: land the raw event straight in the
    # in-memory buffer (no DB round trip on the request path); the SSE
    # stream drains it to push to connected map clients.
    push_sos_event(
        {
            "incident_id": incident_id,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "tracking_metrics": payload.get("tracking_metrics"),
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    response = deepcopy(SOS_RESPONSE)
    response["incident_id"] = incident_id
    return jsonify(response)


@bp.delete("/api/v1/user/account")
@require_bearer_auth
def delete_account():
    """Permanently delete the caller's account. A single DELETE on `users`
    inside one transaction — FK ON DELETE CASCADE constraints (medical_profiles,
    user_favorite_venues, notification_preferences, etc.) remove every other
    user-owned row automatically. No mock fallback here: unlike read
    endpoints, silently returning a fake success on a DB failure would claim
    data was deleted when it wasn't, so any failure propagates as a 500
    instead — db.db_transaction() rolls back and re-raises on exception."""
    with db.db_transaction() as cursor:
        cursor.execute("DELETE FROM users WHERE user_id = %s", (g.user_id,))

    return jsonify(deepcopy(DELETE_ACCOUNT_RESPONSE))


@bp.get("/api/v1/user/medical-passport")
@require_bearer_auth
def get_medical_passport():
    """English is always the passport's common emergency language; the
    bilingual second language comes from the caller's own spoken_languages
    profile field (never a fixed default) with an explicit fallback flag
    when they haven't set one. ?language= remains available as an explicit
    override for previewing a specific language."""
    with db.db_cursor() as cursor:
        cursor.execute("SELECT spoken_languages FROM users WHERE user_id = %s", (g.user_id,))
        row = cursor.fetchone()

    spoken_languages = _parse_spoken_languages(row["spoken_languages"]) if row else []
    second_language = _second_spoken_language_code(spoken_languages)

    response = deepcopy(MEDICAL_PASSPORT_RESPONSE)
    override = request.args.get("language")
    if override:
        response["language"] = override
        response["fallback_used"] = False
    elif second_language:
        response["language"] = second_language
        response["fallback_used"] = False
    else:
        response["language"] = "en"
        response["fallback_used"] = True

    return jsonify(response)

from copy import deepcopy
import json
import uuid
from datetime import datetime, timezone

import pymysql
from flask import Blueprint, g, jsonify, request

import db
from sos_buffer import push_sos_event
from auth import require_api_key, require_bearer_auth, web_readonly_blocked
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


def _format_profile(row: dict) -> dict:
    raw_languages = row["spoken_languages"]
    spoken_languages = json.loads(raw_languages) if raw_languages else []

    return {
        "user_id": row["user_id"],
        "email": row["email"],
        # DB column is display_name; the client contract calls it full_name.
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
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

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
    blocked = web_readonly_blocked()
    if blocked:
        return blocked

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
@require_api_key
def get_medical_passport():
    response = deepcopy(MEDICAL_PASSPORT_RESPONSE)

    language = request.args.get("language")
    if language:
        response["language"] = language

    return jsonify(response)

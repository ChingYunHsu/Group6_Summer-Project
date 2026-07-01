import json
from copy import deepcopy

from flask import Blueprint, g, jsonify, request

import db
from auth import require_bearer_auth


bp = Blueprint("medical", __name__)

SCALAR_FIELDS = {"date_of_birth", "gender", "address", "blood_type"}
JSON_FIELDS = {
    "severe_allergies",
    "conditions",
    "medications",
    "emergency_contacts",
}
EDITABLE_FIELDS = SCALAR_FIELDS | JSON_FIELDS

DEFAULT_PROFILE = {
    "date_of_birth": None,
    "gender": None,
    "address": None,
    "blood_type": None,
    "severe_allergies": [],
    "conditions": [],
    "medications": [],
    "emergency_contacts": [],
}

SELECT_COLUMNS = (
    "date_of_birth",
    "gender",
    "address",
    "blood_type",
    "severe_allergies",
    "conditions",
    "medications",
    "emergency_contacts",
)


def _reject_explicit_user_id():
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


def _serialize_profile(row: dict | None) -> dict:
    profile = deepcopy(DEFAULT_PROFILE)
    if not row:
        return profile

    for field in SCALAR_FIELDS:
        value = row.get(field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        profile[field] = value

    for field in JSON_FIELDS:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, str):
            profile[field] = json.loads(value)
        else:
            profile[field] = value

    return profile


def _db_value(field: str, value):
    if field in JSON_FIELDS and value is not None:
        return json.dumps(value)
    return value


@bp.get("/api/v1/user/medical-profile")
@require_bearer_auth
def get_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    with db.db_cursor() as cursor:
        cursor.execute(
            "SELECT date_of_birth, gender, address, blood_type, severe_allergies, "
            "conditions, medications, emergency_contacts "
            "FROM user_medical_profiles WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    return jsonify(_serialize_profile(row))


@bp.put("/api/v1/user/medical-profile")
@require_bearer_auth
def upsert_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    payload = request.get_json(silent=True) or {}
    invalid_fields = sorted(field for field in payload if field not in EDITABLE_FIELDS)
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
            "SELECT user_id FROM user_medical_profiles WHERE user_id = %s FOR UPDATE",
            (g.user_id,),
        )
        exists = cursor.fetchone()

        if exists:
            set_fields = [field for field in SELECT_COLUMNS if field in payload]
            set_clause = ", ".join(f"{field} = %s" for field in set_fields)
            values = [_db_value(field, payload[field]) for field in set_fields]
            cursor.execute(
                f"UPDATE user_medical_profiles SET {set_clause} WHERE user_id = %s",
                (*values, g.user_id),
            )
        else:
            profile = deepcopy(DEFAULT_PROFILE)
            for field in SELECT_COLUMNS:
                if field in payload:
                    profile[field] = payload[field]

            values = [_db_value(field, profile[field]) for field in SELECT_COLUMNS]
            cursor.execute(
                "INSERT INTO user_medical_profiles "
                "(user_id, date_of_birth, gender, address, blood_type, severe_allergies, "
                "conditions, medications, emergency_contacts) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (g.user_id, *values),
            )

        cursor.execute(
            "SELECT date_of_birth, gender, address, blood_type, severe_allergies, "
            "conditions, medications, emergency_contacts "
            "FROM user_medical_profiles WHERE user_id = %s",
            (g.user_id,),
        )
        row = cursor.fetchone()

    return jsonify(_serialize_profile(row))


@bp.delete("/api/v1/user/medical-profile")
@require_bearer_auth
def delete_medical_profile():
    rejected = _reject_explicit_user_id()
    if rejected:
        return rejected

    with db.db_transaction() as cursor:
        cursor.execute("DELETE FROM user_medical_profiles WHERE user_id = %s", (g.user_id,))

    return "", 204

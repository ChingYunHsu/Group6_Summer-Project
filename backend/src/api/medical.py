"""Medical Profile API endpoints for ClearPath.

Implements GET/PUT/DELETE for user medical profiles.
All endpoints require JWT authentication via @require_auth decorator.
Data is stored in encrypted user_medical_profiles table.
"""

import json

from flask import Blueprint, g, jsonify, request

from auth import require_auth
from db import get_db_conn

bp = Blueprint("medical", __name__)

# Allowed fields for medical profile
ALLOWED_FIELDS = {
    "date_of_birth",
    "gender",
    "address",
    "blood_type",
    "allergies",
    "medical_conditions",
    "emergency_contacts",
}

# JSON fields that need serialization
JSON_FIELDS = {"allergies", "medical_conditions", "emergency_contacts"}

# Date fields validation
DATE_FIELDS = {"date_of_birth"}


def _validate_blood_type(blood_type: str) -> bool:
    """Validate blood type format."""
    valid_types = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
    return blood_type in valid_types


def _serialize_profile(row: dict) -> dict:
    """Convert database row to API response format."""
    profile = {}
    for field in ALLOWED_FIELDS:
        value = row.get(field)
        if value is None:
            profile[field] = None
        elif field in JSON_FIELDS and isinstance(value, str):
            try:
                profile[field] = json.loads(value) # 数据库字符串——> JSON对象
            except json.JSONDecodeError:
                profile[field] = value
        else:
            profile[field] = value
    return profile


@bp.get("/api/v1/user/medical-profile")
@require_auth
def get_medical_profile():
    """Get current user's medical profile.

    Returns:
        200: Medical profile object (empty if no profile exists).
        401: Invalid or missing token.
    """
    user_id = g.user_id

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT date_of_birth, gender, address,
                          blood_type, allergies, medical_conditions,
                          emergency_contacts
                   FROM user_medical_profiles
                   WHERE user_id = %s""",
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
                return jsonify({})

            columns = [
                "date_of_birth", "gender", "address",
                "blood_type", "allergies", "medical_conditions",
                "emergency_contacts",
            ]
            row_dict = dict(zip(columns, row))
            # Convert date to string
            if row_dict.get("date_of_birth"):
                row_dict["date_of_birth"] = row_dict["date_of_birth"].isoformat()
            return jsonify(_serialize_profile(row_dict))

    finally:
        conn.close()


@bp.put("/api/v1/user/medical-profile")
@require_auth
def put_medical_profile():
    """Create or update current user's medical profile (upsert).

    Request body (all fields optional):
        date_of_birth (str): Date of birth (YYYY-MM-DD).
        gender (str): Gender.
        address (str): Home address.
        blood_type (str): Blood type (A+, A-, B+, B-, AB+, AB-, O+, O-).
        allergies (list): List of allergies.
        medical_conditions (list): List of medical conditions.
        emergency_contacts (list): List of emergency contacts.

    Returns:
        200: Updated medical profile.
        400: Validation error.
        401: Invalid or missing token.
    """
    user_id = g.user_id
    payload = request.get_json(silent=True) or {}

    # Filter to allowed fields
    update_fields = {k: v for k, v in payload.items() if k in ALLOWED_FIELDS}

    if not update_fields:
        return jsonify({"error": "No valid fields provided."}), 400

    # Validate blood_type if provided
    if "blood_type" in update_fields and update_fields["blood_type"] is not None:
        if not _validate_blood_type(update_fields["blood_type"]):
            return jsonify({"error": "Invalid blood type. Must be one of: A+, A-, B+, B-, AB+, AB-, O+, O-"}), 400

    # Validate date_of_birth format if provided
    if "date_of_birth" in update_fields and update_fields["date_of_birth"] is not None:
        from datetime import datetime
        try:
            datetime.strptime(update_fields["date_of_birth"], "%Y-%m-%d")
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid date_of_birth format. Must be YYYY-MM-DD."}), 400

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Check if profile exists
            cur.execute(
                "SELECT user_id FROM user_medical_profiles WHERE user_id = %s",
                (user_id,),
            )
            exists = cur.fetchone()

            if exists:
                # Update existing profile
                set_clauses = []
                values = []
                for field, value in update_fields.items():
                    if field in JSON_FIELDS and value is not None:
                        set_clauses.append(f"{field} = %s")
                        values.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{field} = %s")
                        values.append(value)

                values.append(user_id)
                cur.execute(
                    f"UPDATE user_medical_profiles SET {', '.join(set_clauses)} WHERE user_id = %s",
                    values,
                )
            else:
                # Insert new profile
                fields = list(update_fields.keys())
                values = []
                for field in fields:
                    value = update_fields[field]
                    if field in JSON_FIELDS and value is not None:
                        values.append(json.dumps(value))
                    else:
                        values.append(value)

                placeholders = ", ".join(["%s"] * len(fields))
                field_names = ", ".join(["user_id"] + fields)
                value_placeholders = ", ".join(["%s"] + ["%s"] * len(fields))

                cur.execute(
                    f"INSERT INTO user_medical_profiles ({field_names}) VALUES ({value_placeholders})",
                    [user_id] + values,
                )

            conn.commit()

            # Return updated profile
            cur.execute(
                """SELECT date_of_birth, gender, address,
                          blood_type, allergies, medical_conditions,
                          emergency_contacts
                   FROM user_medical_profiles
                   WHERE user_id = %s""",
                (user_id,),
            )
            row = cur.fetchone()
            columns = [
                "date_of_birth", "gender", "address",
                "blood_type", "allergies", "medical_conditions",
                "emergency_contacts",
            ]
            row_dict = dict(zip(columns, row))
            # Convert date to string
            if row_dict.get("date_of_birth"):
                row_dict["date_of_birth"] = row_dict["date_of_birth"].isoformat()
            return jsonify(_serialize_profile(row_dict))

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Failed to update profile.", "detail": str(e)}), 500
    finally:
        conn.close()


@bp.delete("/api/v1/user/medical-profile")
@require_auth
def delete_medical_profile():
    """Delete current user's medical profile.

    Returns:
        204: Profile deleted successfully.
        401: Invalid or missing token.
    """
    user_id = g.user_id

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_medical_profiles WHERE user_id = %s",
                (user_id,),
            )
            conn.commit()
            return "", 204

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Failed to delete profile.", "detail": str(e)}), 500
    finally:
        conn.close()

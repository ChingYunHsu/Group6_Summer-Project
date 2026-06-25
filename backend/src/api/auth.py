import uuid
from copy import deepcopy

import pymysql
from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

import token_blacklist
from auth import ACCESS_TOKEN_TTL, SESSIONS, issue_access_token, require_bearer_auth
from db import db_cursor, db_transaction
from mock_data import AUTH_LOGIN_RESPONSE, AUTH_RESET_PASSWORD_RESPONSE


bp = Blueprint("auth", __name__)


def _issue_token_response(user_id: str, is_guest: bool = False) -> dict:
    """Issue a real JWT (for require_bearer_auth) and mirror it into SESSIONS
    (for get_current_session), so both auth checks accept the same token."""
    access_token = issue_access_token(user_id)
    SESSIONS[access_token] = {"user_id": user_id, "is_guest": is_guest}

    response = deepcopy(AUTH_LOGIN_RESPONSE)
    response["access_token"] = access_token
    response["refresh_token"] = f"mock_refresh_token_{user_id}"
    response["user_id"] = user_id
    response["expires_in"] = int(ACCESS_TOKEN_TTL.total_seconds())
    return response


@bp.post("/api/v1/auth/register")
def register_user():
    payload = request.get_json(silent=True) or {}

    required_fields = ["full_name", "email", "password"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    if not isinstance(payload.get("password"), str) or len(payload["password"]) < 8:
        return jsonify({"error": "Validation failed.", "missing_fields": [], "invalid_fields": ["password"]}), 400

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(payload["password"])

    try:
        with db_transaction() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE email = %s", (payload["email"],))
            if cursor.fetchone():
                return jsonify({"error": "Email already registered."}), 409

            cursor.execute(
                "INSERT INTO users (user_id, email, password_hash, display_name) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, payload["email"], password_hash, payload["full_name"]),
            )
    except pymysql.err.IntegrityError:
        # Race: another request registered this email between our check and insert.
        return jsonify({"error": "Email already registered."}), 409

    response = _issue_token_response(user_id)
    response["finish_profile_prompt"] = True
    return jsonify(response), 201


@bp.post("/api/v1/auth/login")
def login():
    payload = request.get_json(silent=True) or {}

    required_fields = ["email", "password"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    with db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id, password_hash FROM users WHERE email = %s",
            (payload["email"],),
        )
        user = cursor.fetchone()

    if not user or not check_password_hash(user["password_hash"], payload["password"]):
        return jsonify({"error": "Unauthorized. Invalid email or password."}), 401

    return jsonify(_issue_token_response(user["user_id"]))


@bp.post("/api/v1/auth/logout")
@require_bearer_auth
def logout():
    """Revoke the presented access token by blacklisting its signature in Redis."""
    token_blacklist.blacklist_token(g.token, g.token_payload["exp"])
    SESSIONS.pop(g.token, None)
    return jsonify({"message": "Logged out."})


@bp.post("/api/v1/auth/guest")
def create_guest_session():
    """Issue temporary credentials for a guest session."""
    guest_id = f"guest_{len(SESSIONS) + 1}"

    response = _issue_token_response(guest_id, is_guest=True)
    response["finish_profile_prompt"] = False
    return jsonify(response), 201


@bp.post("/api/v1/auth/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}

    if "email" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["email"]}), 400

    return jsonify(deepcopy(AUTH_RESET_PASSWORD_RESPONSE))

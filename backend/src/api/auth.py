from copy import deepcopy

from flask import Blueprint, jsonify, request

from auth import ACCESS_TOKEN_TTL, SESSIONS, issue_access_token
from mock_data import AUTH_LOGIN_RESPONSE, AUTH_RESET_PASSWORD_RESPONSE, AUTH_USERS


bp = Blueprint("auth", __name__)


def _next_user_id() -> str:
    user_numbers = []
    for user in AUTH_USERS:
        user_id = user.get("user_id", "")
        if user_id.startswith("u_"):
            try:
                user_numbers.append(int(user_id.removeprefix("u_")))
            except ValueError:
                continue

    next_number = max(user_numbers, default=1000) + 1
    return f"u_{next_number}"


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

    if any(user["email"] == payload["email"] for user in AUTH_USERS):
        return jsonify({"error": "Email already registered."}), 409

    user = {
        "user_id": _next_user_id(),
        "full_name": payload["full_name"],
        "email": payload["email"],
        "password": payload["password"],
    }
    AUTH_USERS.append(user)

    response = _issue_token_response(user["user_id"])
    response["finish_profile_prompt"] = True
    return jsonify(response), 201


@bp.post("/api/v1/auth/login")
def login():
    payload = request.get_json(silent=True) or {}

    required_fields = ["email", "password"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    user = next(
        (
            user
            for user in AUTH_USERS
            if user["email"] == payload["email"] and user["password"] == payload["password"]
        ),
        None,
    )
    if not user:
        return jsonify({"error": "Unauthorized. Invalid email or password."}), 401

    return jsonify(_issue_token_response(user["user_id"]))


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

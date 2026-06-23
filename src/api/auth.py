from flask import Blueprint, jsonify, request

from auth import ACCESS_TOKEN_TTL, issue_access_token
from mock_data import AUTH_USERS


bp = Blueprint("auth", __name__)


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

    return jsonify(
        {
            "access_token": issue_access_token(user["user_id"]),
            "token_type": "bearer",
            "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
            "user_id": user["user_id"],
        }
    )

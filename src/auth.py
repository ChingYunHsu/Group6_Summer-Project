"""Shared authentication decorators for ClearPath backend.

Provides:
- require_api_key: API key validation (existing)
- require_auth: JWT Bearer token validation (new)
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request


def require_api_key(view_func):
    """Check X-API-Key header against configured API key."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("API_KEY", "")
        provided = request.headers.get("X-API-Key", "")

        if not expected:
            return view_func(*args, **kwargs)

        if provided != expected:
            return jsonify({"error": "Unauthorized. Invalid API key."}), 401

        return view_func(*args, **kwargs)

    return wrapped


def require_auth(view_func):
    """Check Authorization: Bearer <token> header and validate JWT.

    Sets g.user_id and g.user_email on success.
    JWT payload must contain 'sub' (user_id) and 'email'.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header."}), 401

        token = auth_header[7:]  # Strip "Bearer "
        if not token:
            return jsonify({"error": "Missing token."}), 401

        secret = current_app.config.get("JWT_SECRET_KEY", "")
        if not secret:
            return jsonify({"error": "Server misconfiguration."}), 500

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."}), 401

        g.user_id = payload.get("sub")
        g.user_email = payload.get("email")
        if not g.user_id:
            return jsonify({"error": "Token missing user ID."}), 401

        return view_func(*args, **kwargs)

    return wrapped


def generate_token(user_id: str, email: str) -> str:
    """Generate a JWT access token for the given user.

    Args:
        user_id: The user's unique ID.
        email: The user's email address.

    Returns:
        Encoded JWT string.
    """
    secret = current_app.config.get("JWT_SECRET_KEY", "")
    expiration_hours = current_app.config.get("JWT_EXPIRATION_HOURS", 24)

    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiration_hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def web_readonly_blocked():
    """Fix 4: write endpoints reject requests from the read-only Web client."""
    if request.headers.get("X-Client-Origin", "").lower() == "web":
        return jsonify({"error": "Forbidden. This action is not available on the Web client."}), 403

    return None

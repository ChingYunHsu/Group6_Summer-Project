from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

import token_blacklist

ACCESS_TOKEN_TTL = timedelta(hours=1)

# Mock in-memory session store: access_token -> {"user_id": str, "is_guest": bool}
SESSIONS = {}


def get_current_session():
    """Look up the session for the bearer token on the current request, if any."""
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None

    token = header[len("Bearer "):].strip()
    return SESSIONS.get(token)


def require_api_key(view_func):
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


def issue_access_token(user_id: str) -> str:
    """Sign a short-lived JWT identifying user_id, per Fix 1 (BearerAuth migration)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    secret = current_app.config.get("JWT_SECRET", "")
    return jwt.encode(payload, secret, algorithm="HS256")


def require_bearer_auth(view_func):
    """Global token verification gateway: parses the `Authorization: Bearer
    <token>` header, verifies the JWT signature and expiry, rejects tokens
    revoked via logout, and populates the request-scoped session context
    (g.user_id, g.token, g.token_payload) from the sub claim."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.lower().startswith("bearer "):
            return jsonify({"error": "Unauthorized. Bearer token required."}), 401

        token = header[len("Bearer "):].strip()
        if not token:
            return jsonify({"error": "Unauthorized. Bearer token required."}), 401

        secret = current_app.config.get("JWT_SECRET", "")

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Unauthorized. Token expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized. Invalid token."}), 401

        if token_blacklist.is_blacklisted(token):
            return jsonify({"error": "Unauthorized. Token has been revoked."}), 401

        g.user_id = payload.get("sub")
        g.token = token
        g.token_payload = payload
        return view_func(*args, **kwargs)

    return wrapped


def web_readonly_blocked():
    """Fix 4: write endpoints reject requests from the read-only Web client."""
    if request.headers.get("X-Client-Origin", "").lower() == "web":
        return jsonify({"error": "Forbidden. This action is not available on the Web client."}), 403

    return None

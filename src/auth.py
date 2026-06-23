from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

ACCESS_TOKEN_TTL = timedelta(hours=1)


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
    """Verify a signed JWT bearer token and expose the user id as g.user_id."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.lower().startswith("bearer "):
            return jsonify({"error": "Unauthorized. Bearer token required."}), 401

        token = header[len("Bearer "):].strip()
        secret = current_app.config.get("JWT_SECRET", "")

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Unauthorized. Token expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized. Invalid token."}), 401

        g.user_id = payload.get("sub")
        return view_func(*args, **kwargs)

    return wrapped

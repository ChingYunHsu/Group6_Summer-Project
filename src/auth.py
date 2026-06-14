from functools import wraps

from flask import current_app, jsonify, request

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


def web_readonly_blocked():
    """Fix 4: write endpoints reject requests from the read-only Web client."""
    if request.headers.get("X-Client-Origin", "").lower() == "web":
        return jsonify({"error": "Forbidden. This action is not available on the Web client."}), 403

    return None

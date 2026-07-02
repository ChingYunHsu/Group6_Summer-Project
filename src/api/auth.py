"""Authentication API endpoints for ClearPath.

Implements register and login against MySQL users table with bcrypt password hashing.
Returns JWT access tokens on successful authentication.
"""

import uuid
from datetime import datetime, timezone

import bcrypt
from flask import Blueprint, jsonify, request

from auth import generate_token
from db import get_db_conn

bp = Blueprint("auth", __name__)


def _hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _generate_user_id() -> str:
    """Generate a unique user ID."""
    return f"u_{uuid.uuid4().hex[:12]}"


@bp.post("/api/v1/auth/register")
def register_user():
    """Register a new user.

    Request body:
        full_name (str): User's display name.
        email (str): User's email address.
        password (str): Password (min 8 chars).

    Returns:
        201: access_token, user_id, finish_profile_prompt.
        400: Validation error.
        409: Email already registered.
    """
    payload = request.get_json(silent=True) or {}

    # Validate required fields
    required_fields = ["full_name", "email", "password"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    # Validate password length
    password = payload["password"]
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Validation failed.", "missing_fields": [], "invalid_fields": ["password"]}), 400

    email = payload["email"].strip().lower()
    full_name = payload["full_name"].strip()

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Check if email already exists
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"error": "Email already registered."}), 409

            # Insert new user
            user_id = _generate_user_id()
            password_hash = _hash_password(password)
            now = datetime.now(timezone.utc)

            cur.execute(
                """INSERT INTO users (user_id, email, password_hash, display_name, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, email, password_hash, full_name, now, now),
            )
            conn.commit()

            # Generate JWT
            token = generate_token(user_id, email)

            return jsonify({
                "access_token": token,
                "token_type": "Bearer",
                "user_id": user_id,
                "finish_profile_prompt": True,
            }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Registration failed.", "detail": str(e)}), 500
    finally:
        conn.close()


@bp.post("/api/v1/auth/login")
def login_user():
    """Login with email and password.

    Request body:
        email (str): User's email address.
        password (str): User's password.

    Returns:
        200: access_token, user_id.
        400: Validation error.
        401: Invalid credentials.
    """
    payload = request.get_json(silent=True) or {}

    # Validate required fields
    required_fields = ["email", "password"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return jsonify({"error": "Validation failed.", "missing_fields": missing}), 400

    email = payload["email"].strip().lower()
    password = payload["password"]

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # Find user by email
            cur.execute(
                "SELECT user_id, password_hash, account_status FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

            if not row:
                return jsonify({"error": "Invalid credentials."}), 401

            user_id, password_hash, account_status = row

            # Check account status
            if account_status != "active":
                return jsonify({"error": "Account is not active."}), 403

            # Verify password
            if not _check_password(password, password_hash):
                return jsonify({"error": "Invalid credentials."}), 401

            # Generate JWT
            token = generate_token(user_id, email)

            return jsonify({
                "access_token": token,
                "token_type": "Bearer",
                "user_id": user_id,
            })

    except Exception as e:
        return jsonify({"error": "Login failed.", "detail": str(e)}), 500
    finally:
        conn.close()


@bp.post("/api/v1/auth/reset-password")
def reset_password():
    """Reset password (placeholder - not implemented in this phase)."""
    payload = request.get_json(silent=True) or {}

    if "email" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["email"]}), 400

    # Placeholder response - actual email sending not implemented
    return jsonify({
        "message": "If the email exists, a reset link has been sent.",
        "email": payload["email"],
    })

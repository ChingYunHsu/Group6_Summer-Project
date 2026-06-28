"""Unit tests for the register/login business logic with the MySQL layer
faked out, so this runs without a live database (unlike the @integration
tests in test_auth_login.py / test_auth_register.py, which hit real MySQL)."""

from contextlib import contextmanager

import pytest

import api.auth as auth_module
from werkzeug.security import generate_password_hash


class _FakeCursor:
    def __init__(self, users: dict):
        self._users = users
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT 1 FROM users WHERE email"):
            self._result = {"1": 1} if params[0] in self._users else None
        elif query.startswith("INSERT INTO users"):
            user_id, email, password_hash, _full_name = params
            self._users[email] = {"user_id": user_id, "password_hash": password_hash}
            self._result = None
        elif query.startswith("SELECT user_id, password_hash FROM users WHERE email"):
            self._result = self._users.get(params[0])
        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result


@pytest.fixture
def fake_users_db(monkeypatch):
    users = {}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(users)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(users)

    monkeypatch.setattr(auth_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(auth_module, "db_transaction", fake_db_transaction)
    return users


def test_register_then_login_round_trip(client, fake_users_db):
    register = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Fake User", "email": "fake@example.com", "password": "Password123"},
    )
    assert register.status_code == 201

    stored = fake_users_db["fake@example.com"]
    assert stored["password_hash"] != "Password123"  # must be hashed, not plaintext

    login = client.post(
        "/api/v1/auth/login", json={"email": "fake@example.com", "password": "Password123"}
    )
    assert login.status_code == 200
    assert login.get_json()["user_id"] == stored["user_id"]


def test_register_duplicate_email_rejected(client, fake_users_db):
    fake_users_db["fake@example.com"] = {
        "user_id": "existing-id",
        "password_hash": generate_password_hash("Password123"),
    }

    resp = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Fake User", "email": "fake@example.com", "password": "Password123"},
    )

    assert resp.status_code == 409


def test_login_wrong_password_rejected(client, fake_users_db):
    fake_users_db["fake@example.com"] = {
        "user_id": "existing-id",
        "password_hash": generate_password_hash("Password123"),
    }

    resp = client.post(
        "/api/v1/auth/login", json={"email": "fake@example.com", "password": "wrong"}
    )

    assert resp.status_code == 401

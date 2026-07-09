"""Unit tests for GET/PUT /api/v1/user/profile (Tier 1), with the MySQL
layer faked out so this runs without a live database.

The fake cursor only knows how to answer queries against the `users` table.
Any query touching `medical_profiles` (Tier 2) raises AssertionError, which
is the actual proof that the standard profile handlers never reach the
clinical/encrypted data path — not just that they happen not to import it.
"""

from contextlib import contextmanager

import pytest

import api.user as user_module
from auth import issue_access_token

URL = "/api/v1/user/profile"


class _FakeCursor:
    def __init__(self, users: dict):
        self._users = users
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if "medical_profiles" in query:
            raise AssertionError(
                f"Tier 1 profile handler must never touch medical_profiles, got: {query!r}"
            )

        if query.startswith("SELECT user_id, email, display_name, phone, nationality, spoken_languages FROM users"):
            self._result = self._users.get(params[0])
        elif query.startswith("UPDATE users SET"):
            user_id = params[-1]
            row = self._users.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "email": "test@example.com",
                    "display_name": "Test User",
                    "phone": None,
                    "nationality": None,
                    "spoken_languages": None,
                },
            )
            # values are positional in the same order as the SET clause fields
            field_names = [c.split(" = ")[0] for c in query.split("SET ", 1)[1].split(" WHERE")[0].split(", ")]
            for field, value in zip(field_names, params[:-1]):
                row[field] = value
            self._result = None
        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result


@pytest.fixture
def fake_users_table(monkeypatch):
    users = {
        "u_alice": {
            "user_id": "u_alice",
            "email": "alice@example.com",
            "display_name": "Alice",
            "phone": "+1-555-0100",
            "nationality": "Irish",
            "spoken_languages": ["English"],
        }
    }

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(users)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(users)

    monkeypatch.setattr(user_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)
    return users


def _token_for(app, user_id):
    with app.app_context():
        return issue_access_token(user_id)


def test_get_profile_returns_tier1_fields_only(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["user_id"] == "u_alice"
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice"
    assert data["phone"] == "+1-555-0100"
    assert data["nationality"] == "Irish"
    assert "blood_type" not in data
    assert "conditions" not in data
    assert "allergies" not in data


def test_update_profile_writes_only_tier1_fields(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        URL,
        json={"phone": "+1-555-9999", "nationality": "French", "spoken_languages": ["English", "French"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["phone"] == "+1-555-9999"
    assert data["nationality"] == "French"
    assert data["spoken_languages"] == ["English", "French"]
    assert fake_users_table["u_alice"]["phone"] == "+1-555-9999"


def test_update_profile_rejects_clinical_fields(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        URL,
        json={"blood_type": "O+", "conditions": ["Asthma"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert set(resp.get_json()["invalid_fields"]) == {"blood_type", "conditions"}


def test_update_profile_with_no_fields_does_not_crash(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.put(URL, json={}, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json()["phone"] == "+1-555-0100"  # unchanged


def test_profile_requires_bearer_token(client):
    resp = client.get(URL)

    assert resp.status_code == 401


def test_profile_update_never_touches_medical_profiles_table(client, app, monkeypatch):
    """Direct proof for the task requirement: Tier 2 stays untouched by Tier 1 writes."""
    users = {
        "u_alice": {
            "user_id": "u_alice",
            "email": "alice@example.com",
            "display_name": "Alice",
            "phone": None,
            "nationality": None,
            "spoken_languages": None,
        }
    }
    medical_profiles_queried = {"called": False}

    class _AssertingCursor(_FakeCursor):
        def execute(self, query, params=()):
            if "medical_profiles" in " ".join(query.split()):
                medical_profiles_queried["called"] = True
            super().execute(query, params)

    @contextmanager
    def fake_db_transaction():
        yield _AssertingCursor(users)

    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)

    token = _token_for(app, "u_alice")
    resp = client.put(
        URL,
        json={"phone": "+1-555-1111", "nationality": "Spanish", "spoken_languages": ["Spanish"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert medical_profiles_queried["called"] is False

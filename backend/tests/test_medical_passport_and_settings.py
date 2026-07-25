"""Unit tests for GET /api/v1/user/medical-passport and GET/PUT
/api/v1/user/settings, with the MySQL layer faked out.

Covers two fixes:
  - medical-passport's bilingual second language is derived from the
    caller's own `spoken_languages` profile field (never a fixed default),
    with an explicit `fallback_used` flag when none is set.
  - settings' `selected_language` is per-user and DB-backed
    (`users.preferred_language`), not a single dict shared by every caller,
    and PUT requires the same BearerAuth as GET.
"""

from contextlib import contextmanager

import pytest

import api.user as user_module
from auth import issue_access_token

SETTINGS_URL = "/api/v1/user/settings"
PASSPORT_URL = "/api/v1/user/medical-passport"


class _FakeCursor:
    def __init__(self, users: dict):
        self._users = users
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT spoken_languages FROM users"):
            row = self._users.get(params[0])
            self._result = {"spoken_languages": row["spoken_languages"]} if row else None
        elif query.startswith("SELECT preferred_language FROM users"):
            row = self._users.get(params[0])
            self._result = {"preferred_language": row["preferred_language"]} if row else None
        elif query.startswith("UPDATE users SET preferred_language"):
            code, user_id = params
            self._users.setdefault(user_id, {})["preferred_language"] = code
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
            "spoken_languages": ["English", "French"],
            "preferred_language": "en",
        },
        "u_bob": {
            "user_id": "u_bob",
            "spoken_languages": ["English"],
            "preferred_language": None,
        },
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


# ── Medical Passport ────────────────────────────────────────────────────


def test_medical_passport_requires_bearer_token(client):
    resp = client.get(PASSPORT_URL)

    assert resp.status_code == 401


def test_medical_passport_uses_second_spoken_language(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.get(PASSPORT_URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "fr"
    assert data["fallback_used"] is False


def test_medical_passport_falls_back_when_no_second_language(client, app, fake_users_table):
    token = _token_for(app, "u_bob")

    resp = client.get(PASSPORT_URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "en"
    assert data["fallback_used"] is True


def test_medical_passport_language_query_param_overrides_profile(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.get(
        f"{PASSPORT_URL}?language=es",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "es"
    assert data["fallback_used"] is False


# ── Settings ─────────────────────────────────────────────────────────────


def test_settings_requires_bearer_token_on_get_and_put(client):
    assert client.get(SETTINGS_URL).status_code == 401
    assert client.put(SETTINGS_URL, json={}).status_code == 401


def test_get_settings_reflects_per_user_preferred_language(client, app, fake_users_table):
    alice_token = _token_for(app, "u_alice")
    bob_token = _token_for(app, "u_bob")

    alice_resp = client.get(SETTINGS_URL, headers={"Authorization": f"Bearer {alice_token}"})
    bob_resp = client.get(SETTINGS_URL, headers={"Authorization": f"Bearer {bob_token}"})

    assert alice_resp.get_json()["selected_language"] == "en"
    # Bob has no preferred_language set in the DB — falls back to "en", not
    # whatever the last caller happened to write (proves this isn't a
    # single dict shared across every user).
    assert bob_resp.get_json()["selected_language"] == "en"
    assert bob_resp.get_json()["selected_language_native"] == "English"


def test_put_settings_updates_only_the_calling_users_language(client, app, fake_users_table):
    alice_token = _token_for(app, "u_alice")
    bob_token = _token_for(app, "u_bob")

    resp = client.put(
        SETTINGS_URL,
        json={"selected_language": "fr"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["selected_language"] == "fr"
    assert data["selected_language_native"] == "Français"

    bob_resp = client.get(SETTINGS_URL, headers={"Authorization": f"Bearer {bob_token}"})
    assert bob_resp.get_json()["selected_language"] == "en"


def test_put_settings_rejects_unsupported_language_code(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        SETTINGS_URL,
        json={"selected_language": "xx"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert "selected_language" in resp.get_json()["invalid_fields"]


def test_put_settings_ignores_client_supplied_native_name(client, app, fake_users_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        SETTINGS_URL,
        json={"selected_language": "es", "selected_language_native": "Bogus"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["selected_language_native"] == "Español"

"""Unit tests for /api/v1/user/notification-preferences, with the MySQL
layer faked out so this runs without a live database.

The fake cursor stores notification_preferences as a JSON string (not a
dict), matching what PyMySQL actually hands back for a JSON column — it
does not auto-decode JSON, unlike some other drivers.
"""

import json
from contextlib import contextmanager

import pytest

import api.user as user_module
from auth import issue_access_token

URL = "/api/v1/user/notification-preferences"


class _FakeCursor:
    def __init__(self, table: dict):
        self._table = table
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT notification_preferences FROM users"):
            stored = self._table.get(params[0])
            self._result = {"notification_preferences": stored} if stored is not None else None
        elif query.startswith("UPDATE users SET notification_preferences"):
            preferences_json, user_id = params
            self._table[user_id] = preferences_json
            self._result = None
        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result


@pytest.fixture
def fake_preferences_table(monkeypatch):
    table = {}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(table)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(table)

    monkeypatch.setattr(user_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)
    return table


def _token_for(app, user_id):
    with app.app_context():
        return issue_access_token(user_id)


@pytest.mark.parametrize(
    "payload",
    [
        {"unknown_field": True},
        {"busyness_alerts_enabled": True, "extra_garbage": "nope"},
        {"alert_threshold_percent": 50, "preferred_venue_types": ["bar"], "is_admin": True},
        {"": "blank-key"},
    ],
)
def test_update_notification_preferences_rejects_unknown_fields(client, app, payload):
    token = _token_for(app, "u_alice")

    resp = client.put(URL, json=payload, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 400

    data = resp.get_json()
    assert data["error"] == "Validation failed."
    assert data["missing_fields"] == []
    assert set(data["invalid_fields"]) == {k for k in payload if k not in {
        "busyness_alerts_enabled",
        "push_notifications_enabled",
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "alert_threshold_percent",
        "preferred_venue_types",
        "preferred_boroughs",
    }}


def test_update_notification_preferences_accepts_valid_fields(client, app, fake_preferences_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        URL,
        json={"busyness_alerts_enabled": False, "alert_threshold_percent": 75},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["busyness_alerts_enabled"] is False
    assert data["alert_threshold_percent"] == 75


def test_notification_preferences_requires_bearer_token(client):
    resp = client.put(URL, json={"busyness_alerts_enabled": True})

    assert resp.status_code == 401


def test_get_notification_preferences_defaults_when_none_stored(client, app, fake_preferences_table):
    token = _token_for(app, "u_alice")

    resp = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json()["busyness_alerts_enabled"] is True


def test_update_then_get_round_trips_through_json_string_storage(client, app, fake_preferences_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    client.put(URL, json={"alert_threshold_percent": 42}, headers=headers)

    assert isinstance(fake_preferences_table["u_alice"], str)
    json.loads(fake_preferences_table["u_alice"])  # stored value must be valid JSON text

    get_resp = client.get(URL, headers=headers)
    assert get_resp.get_json()["alert_threshold_percent"] == 42


def test_user_isolation_between_tokens(client, app, fake_preferences_table):
    alice = _token_for(app, "u_alice")
    bob = _token_for(app, "u_bob")

    client.put(
        URL, json={"alert_threshold_percent": 10}, headers={"Authorization": f"Bearer {alice}"}
    )

    bob_resp = client.get(URL, headers={"Authorization": f"Bearer {bob}"})
    assert bob_resp.get_json()["alert_threshold_percent"] != 10

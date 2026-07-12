"""Unit tests for the medical profile endpoints (api/medical.py), with the
MySQL layer faked out so this runs without a live database.

Previously two blueprints both defined /api/v1/user/medical-profile:
user.py's version (querying a nonexistent encrypted_payload column — a
schema mismatch that 500'd) shadowed api/medical.py's correct version
because user_bp is registered before medical_bp in app.py. user.py's
version has been removed; this file now targets the one that's actually
reachable and matches the real medical_profiles schema (004_medical_profiles.sql)."""

from contextlib import contextmanager

import pytest

import api.medical as medical_module
from auth import issue_access_token

URL = "/api/v1/user/medical-profile"


class _FakeCursor:
    def __init__(self, table: dict):
        self._table = table
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT date_of_birth, gender, address, blood_type, allergies, "
                             "conditions, medications, emergency_contacts FROM medical_profiles"):
            self._result = self._table.get(params[-1])
        elif query.startswith("SELECT user_id FROM medical_profiles WHERE user_id = %s FOR UPDATE"):
            self._result = {"user_id": params[0]} if params[0] in self._table else None
        elif query.startswith("UPDATE medical_profiles SET"):
            *values, user_id = params
            row = self._table.setdefault(user_id, {})
            set_fields = [part.split(" = ")[0].strip() for part in query.split("SET ", 1)[1].split(" WHERE ")[0].split(",")]
            for field, value in zip(set_fields, values):
                row[field] = value
            self._result = None
        elif query.startswith("INSERT INTO medical_profiles"):
            user_id = params[0]
            fields = ("date_of_birth", "gender", "address", "blood_type",
                      "allergies", "conditions", "medications", "emergency_contacts")
            self._table[user_id] = dict(zip(fields, params[1:]))
            self._result = None
        elif query.startswith("DELETE FROM medical_profiles"):
            self._table.pop(params[0], None)
            self._result = None
        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result


@pytest.fixture
def fake_profiles_table(monkeypatch):
    table = {}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(table)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(table)

    monkeypatch.setattr(medical_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(medical_module.db, "db_transaction", fake_db_transaction)
    return table


def _token_for(app, user_id):
    with app.app_context():
        return issue_access_token(user_id)


def test_medical_profile_route_is_reachable_and_owned_by_medical_blueprint(app):
    """Regression guard: only one blueprint may register this URL. If
    user_bp ever re-adds a competing route, Flask's routing (first
    registered wins on an exact rule collision) would silently shadow
    api/medical.py's implementation again without raising any error."""
    matching_rules = [rule for rule in app.url_map.iter_rules() if rule.rule == URL]
    assert len(matching_rules) >= 1
    for rule in matching_rules:
        assert rule.endpoint.startswith("medical."), (
            f"{URL} is owned by {rule.endpoint!r}, not the medical blueprint"
        )


def test_get_medical_profile_defaults_when_none_stored(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")

    resp = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json() == {
        "date_of_birth": None,
        "gender": None,
        "address": None,
        "blood_type": None,
        "allergies": [],
        "conditions": [],
        "medications": [],
        "emergency_contacts": [],
    }


def test_upsert_then_get_round_trips(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    put_resp = client.put(
        URL,
        json={"blood_type": "O+", "allergies": ["Penicillin"], "medications": ["Insulin"]},
        headers=headers,
    )
    assert put_resp.status_code == 200
    body = put_resp.get_json()
    assert body["blood_type"] == "O+"
    assert body["allergies"] == ["Penicillin"]
    assert body["medications"] == ["Insulin"]

    get_resp = client.get(URL, headers=headers)
    assert get_resp.get_json()["blood_type"] == "O+"


def test_user_isolation_between_tokens(client, app, fake_profiles_table):
    alice = _token_for(app, "u_alice")
    bob = _token_for(app, "u_bob")

    client.put(URL, json={"blood_type": "A-"}, headers={"Authorization": f"Bearer {alice}"})

    bob_resp = client.get(URL, headers={"Authorization": f"Bearer {bob}"})
    assert bob_resp.get_json()["blood_type"] is None


def test_explicit_user_id_query_param_rejected_on_all_methods(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    get_resp = client.get(f"{URL}?user_id=u_bob", headers=headers)
    put_resp = client.put(f"{URL}?user_id=u_bob", json={"blood_type": "O+"}, headers=headers)
    delete_resp = client.delete(f"{URL}?user_id=u_bob", headers=headers)

    for resp in (get_resp, put_resp, delete_resp):
        assert resp.status_code == 400
        assert "user_id" in resp.get_json()["error"]


def test_delete_removes_profile(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}
    client.put(URL, json={"blood_type": "O+"}, headers=headers)

    delete_resp = client.delete(URL, headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(URL, headers=headers)
    assert get_resp.get_json()["blood_type"] is None


def test_medical_profile_requires_bearer_token(client, fake_profiles_table):
    resp = client.get(URL)

    assert resp.status_code == 401


def test_upsert_rejects_unknown_fields(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")

    resp = client.put(
        URL, json={"blood_type": "O+", "ssn": "123-45-6789"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert resp.get_json()["invalid_fields"] == ["ssn"]

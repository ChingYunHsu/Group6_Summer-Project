"""Unit tests for the Tier 2 encrypted medical profile endpoints, with the
MySQL layer faked out so this runs without a live database."""

from contextlib import contextmanager

import pytest

import api.user as user_module
import medical_crypto
from auth import issue_access_token

URL = "/api/v1/user/medical-profile"


class _FakeCursor:
    def __init__(self, table: dict):
        self._table = table
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT encrypted_payload FROM medical_profiles"):
            self._result = self._table.get(params[0])
        elif query.startswith("INSERT INTO medical_profiles"):
            user_id, encrypted_payload, _ = params
            self._table[user_id] = {"encrypted_payload": encrypted_payload}
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

    monkeypatch.setattr(user_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)
    return table


def _token_for(app, user_id):
    with app.app_context():
        return issue_access_token(user_id)


def test_get_medical_profile_defaults_when_none_stored(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")

    resp = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json() == {"blood_type": None, "conditions": [], "allergies": []}


def test_upsert_then_get_round_trips(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    put_resp = client.put(URL, json={"blood_type": "O+", "allergies": ["Penicillin"]}, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.get_json()["blood_type"] == "O+"

    get_resp = client.get(URL, headers=headers)
    assert get_resp.get_json() == {"blood_type": "O+", "conditions": [], "allergies": ["Penicillin"]}


def test_payload_is_actually_encrypted_at_rest(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    client.put(
        URL, json={"blood_type": "O+", "conditions": ["Asthma"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    stored = fake_profiles_table["u_alice"]["encrypted_payload"]
    assert b"Asthma" not in stored
    assert b"O+" not in stored
    assert medical_crypto.decrypt_profile(stored)["conditions"] == ["Asthma"]


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

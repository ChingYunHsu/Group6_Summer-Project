"""Unit tests for the Tier 2 medical profile endpoints, with the
MySQL layer faked out so this runs without a live database."""

import json
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

        if query.startswith("SELECT date_of_birth, gender, address, blood_type, severe_allergies"):
            self._result = self._table.get(params[0])
        elif query.startswith("SELECT user_id FROM medical_profiles"):
            self._result = {"user_id": params[0]} if params[0] in self._table else None
        elif query.startswith("INSERT INTO medical_profiles"):
            (
                user_id,
                date_of_birth,
                gender,
                address,
                blood_type,
                severe_allergies,
                conditions,
                medications,
                emergency_contacts,
            ) = params
            self._table[user_id] = {
                "date_of_birth": date_of_birth,
                "gender": gender,
                "address": address,
                "blood_type": blood_type,
                "severe_allergies": severe_allergies,
                "conditions": conditions,
                "medications": medications,
                "emergency_contacts": emergency_contacts,
            }
            self._result = None
        elif query.startswith("UPDATE medical_profiles SET"):
            values = list(params)
            user_id = values.pop()
            row = self._table[user_id]
            set_clause = query.removeprefix("UPDATE medical_profiles SET ").removesuffix(
                " WHERE user_id = %s"
            )
            fields = [part.split(" = ")[0] for part in set_clause.split(", ")]
            for field, value in zip(fields, values):
                row[field] = value
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


def test_get_medical_profile_defaults_when_none_stored(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")

    resp = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json() == {
        "date_of_birth": None,
        "gender": None,
        "address": None,
        "blood_type": None,
        "severe_allergies": [],
        "conditions": [],
        "medications": [],
        "emergency_contacts": [],
    }


def test_upsert_then_get_round_trips(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    put_resp = client.put(
        URL,
        json={"blood_type": "O+", "severe_allergies": ["Penicillin"]},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.get_json()["blood_type"] == "O+"

    get_resp = client.get(URL, headers=headers)
    assert get_resp.get_json()["severe_allergies"] == ["Penicillin"]


def test_profile_uses_split_json_columns_at_rest(client, app, fake_profiles_table):
    token = _token_for(app, "u_alice")
    client.put(
        URL,
        json={"blood_type": "O+", "conditions": ["Asthma"], "medications": ["Albuterol"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    stored = fake_profiles_table["u_alice"]
    assert "encrypted_payload" not in stored
    assert json.loads(stored["conditions"]) == ["Asthma"]
    assert json.loads(stored["medications"]) == ["Albuterol"]


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
        URL, json={"blood_type": "O+", "ssn": "123-45-6789", "allergies": ["old"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert resp.get_json()["invalid_fields"] == ["allergies", "ssn"]

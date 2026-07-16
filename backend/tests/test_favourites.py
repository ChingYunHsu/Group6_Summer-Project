"""Unit tests for the per-user, DB-backed favourites endpoints. Previously
GET/POST/DELETE /user/favourites operated on one shared global in-memory
list (no user_id filtering) and add_favourite always echoed the same
hardcoded favourite_id/saved_at regardless of what was added — this locks
in that both are actually fixed."""

from contextlib import contextmanager

import pytest

import api.user as user_module
from auth import issue_access_token


class _FakeCursor:
    def __init__(self, table: dict):
        self._table = table  # {(user_id, venue_id): created_at}
        self._result = None
        self.rowcount = 0

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT ufv.venue_id, ufv.created_at") and "WHERE ufv.user_id = %s AND ufv.venue_id = %s" in query:
            user_id, venue_id = params
            created_at = self._table.get((user_id, venue_id))
            self._result = {"venue_id": venue_id, "created_at": created_at, "level": None} if created_at else None
        elif query.startswith("SELECT ufv.venue_id, ufv.created_at"):
            user_id = params[0]
            rows = [
                {"venue_id": v, "created_at": created_at, "level": None}
                for (u, v), created_at in self._table.items()
                if u == user_id
            ]
            self._result = sorted(rows, key=lambda r: r["created_at"], reverse=True)
        elif query.startswith("INSERT INTO user_favorite_venues"):
            user_id, venue_id = params
            import datetime

            self._table.setdefault((user_id, venue_id), datetime.datetime(2026, 1, 1))
        elif query.startswith("DELETE FROM user_favorite_venues"):
            user_id, venue_id = params
            existed = (user_id, venue_id) in self._table
            self._table.pop((user_id, venue_id), None)
            self.rowcount = 1 if existed else 0
        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result or []


@pytest.fixture
def fake_favourites_table(monkeypatch):
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


def test_favourites_requires_bearer_token(client):
    resp = client.get("/api/v1/user/favourites")
    assert resp.status_code == 401


def test_add_favourite_allowed_from_web_client(client, app, fake_favourites_table):
    """Save Location on the web dashboard must be able to persist —
    favourites are no longer gated by X-Client-Origin: web."""
    token = _token_for(app, "u_alice")
    resp = client.post(
        "/api/v1/user/favourites",
        json={"venue_id": "v_9999"},
        headers={"Authorization": f"Bearer {token}", "X-Client-Origin": "web"},
    )
    assert resp.status_code == 201


def test_delete_favourite_allowed_from_web_client(client, app, fake_favourites_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/user/favourites", json={"venue_id": "v_1"}, headers=headers)

    resp = client.delete(
        "/api/v1/user/favourites/v_1",
        headers={"Authorization": f"Bearer {token}", "X-Client-Origin": "web"},
    )
    assert resp.status_code == 204


def test_add_favourite_returns_the_actual_venue_added(client, app, fake_favourites_table):
    token = _token_for(app, "u_alice")
    resp = client.post(
        "/api/v1/user/favourites", json={"venue_id": "v_9999"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["venue_id"] == "v_9999"
    assert body["favourite_id"] == "fav_v_9999"


def test_favourites_are_scoped_per_user(client, app, fake_favourites_table):
    alice = _token_for(app, "u_alice")
    bob = _token_for(app, "u_bob")

    client.post("/api/v1/user/favourites", json={"venue_id": "v_1"}, headers={"Authorization": f"Bearer {alice}"})

    alice_resp = client.get("/api/v1/user/favourites", headers={"Authorization": f"Bearer {alice}"})
    bob_resp = client.get("/api/v1/user/favourites", headers={"Authorization": f"Bearer {bob}"})

    assert alice_resp.get_json()["count"] == 1
    assert bob_resp.get_json()["count"] == 0


def test_add_favourite_is_idempotent(client, app, fake_favourites_table):
    token = _token_for(app, "u_alice")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/api/v1/user/favourites", json={"venue_id": "v_1"}, headers=headers)
    second = client.post("/api/v1/user/favourites", json={"venue_id": "v_1"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201

    listing = client.get("/api/v1/user/favourites", headers=headers)
    assert listing.get_json()["count"] == 1


def test_delete_favourite_only_removes_the_calling_users_row(client, app, fake_favourites_table):
    alice = _token_for(app, "u_alice")
    bob = _token_for(app, "u_bob")

    client.post("/api/v1/user/favourites", json={"venue_id": "v_1"}, headers={"Authorization": f"Bearer {alice}"})

    # Bob has no such favourite — deleting it for him should 404, not
    # affect Alice's row.
    bob_delete = client.delete("/api/v1/user/favourites/v_1", headers={"Authorization": f"Bearer {bob}"})
    assert bob_delete.status_code == 404

    alice_delete = client.delete("/api/v1/user/favourites/v_1", headers={"Authorization": f"Bearer {alice}"})
    assert alice_delete.status_code == 204

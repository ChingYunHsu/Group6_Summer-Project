"""Unit tests for the transactional account-deletion endpoint. MySQL is
faked out (no live DB needed) — the important behaviors under test are:
identity comes from the bearer token, the DELETE actually runs inside
db.db_transaction(), and any DB failure surfaces as an error instead of a
fabricated success response."""

from contextlib import contextmanager

import pytest

import api.user as user_module
from auth import issue_access_token


class _FakeCursor:
    def __init__(self, deleted: list):
        self._deleted = deleted

    def execute(self, query, params=()):
        query = " ".join(query.split())
        assert query == "DELETE FROM users WHERE user_id = %s"
        self._deleted.append(params[0])


class _RaisingCursor:
    def execute(self, query, params=()):
        raise RuntimeError("simulated FK violation (user_reports not cascaded)")


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = issue_access_token("u_1001")
    return {"Authorization": f"Bearer {token}"}


def test_delete_account_requires_bearer_token(client):
    resp = client.delete("/api/v1/user/account")
    assert resp.status_code == 401


def test_delete_account_deletes_the_authenticated_user_only(client, auth_headers, monkeypatch):
    deleted = []

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(deleted)

    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)

    resp = client.delete("/api/v1/user/account", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "deleted"
    assert deleted == ["u_1001"]  # sub claim from the token, not attacker-suppliable


def test_delete_account_returns_error_when_transaction_fails(client, auth_headers, monkeypatch):
    @contextmanager
    def fake_db_transaction():
        yield _RaisingCursor()

    monkeypatch.setattr(user_module.db, "db_transaction", fake_db_transaction)

    # Must NOT return a fabricated success — a DB failure has to surface
    # (here as an unhandled exception, since app.config["TESTING"] re-raises
    # instead of converting to a 500 response), never a 200 claiming data
    # was deleted when it wasn't.
    with pytest.raises(RuntimeError):
        client.delete("/api/v1/user/account", headers=auth_headers)

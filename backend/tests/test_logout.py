import time

import token_blacklist
from auth import issue_access_token


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None):
        self.store[key] = (value, time.time() + ex if ex else None)
        return True

    def exists(self, key):
        entry = self.store.get(key)
        if entry is None:
            return 0
        _, expires_at = entry
        if expires_at is not None and expires_at < time.time():
            del self.store[key]
            return 0
        return 1


def _fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(token_blacklist, "_get_client", lambda: fake)
    return fake


def test_logout_requires_bearer_token(client, monkeypatch):
    _fake_redis(monkeypatch)

    resp = client.post("/api/v1/auth/logout")

    assert resp.status_code == 401


def test_logout_revokes_token_for_subsequent_requests(client, app, monkeypatch):
    _fake_redis(monkeypatch)

    with app.app_context():
        token = issue_access_token("u_1001")
    headers = {"Authorization": f"Bearer {token}"}

    still_valid = client.get("/api/v1/user/medical-id", headers=headers)
    assert still_valid.status_code == 200

    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    revoked = client.get("/api/v1/user/medical-id", headers=headers)
    assert revoked.status_code == 401
    assert revoked.get_json()["error"] == "Unauthorized. Token has been revoked."


def test_other_tokens_unaffected_by_logout(client, app, monkeypatch):
    _fake_redis(monkeypatch)

    with app.app_context():
        token_a = issue_access_token("u_1001")
        token_b = issue_access_token("u_1002")

    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token_a}"})

    resp = client.get("/api/v1/user/medical-id", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 200

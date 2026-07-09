"""Unit tests for the Redis blacklist module with a fake in-memory Redis
client, so this runs without a live Redis (unlike a real integration test).

Requires the ``redis`` python package (for ``redis.RedisError``) but no
running Redis server. Skipped wholesale when the package is absent so that
collecting the backend test suite never crashes in a minimal env."""

import time

import pytest

redis = pytest.importorskip("redis")

import token_blacklist


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


class _BrokenRedis:
    def set(self, *args, **kwargs):
        raise redis.RedisError("connection refused")

    def exists(self, *args, **kwargs):
        raise redis.RedisError("connection refused")


def test_blacklist_then_is_blacklisted_returns_true(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(token_blacklist, "_get_client", lambda: fake)

    token = "header.payload.signature-abc"
    token_blacklist.blacklist_token(token, exp=int(time.time()) + 60)

    assert token_blacklist.is_blacklisted(token) is True
    assert token_blacklist.is_blacklisted("header.payload.different-signature") is False


def test_blacklist_skips_already_expired_token(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(token_blacklist, "_get_client", lambda: fake)

    token = "header.payload.expired-signature"
    token_blacklist.blacklist_token(token, exp=int(time.time()) - 10)

    assert fake.store == {}


def test_is_blacklisted_fails_open_when_redis_unreachable(monkeypatch):
    monkeypatch.setattr(token_blacklist, "_get_client", lambda: _BrokenRedis())

    assert token_blacklist.is_blacklisted("header.payload.signature") is False


def test_blacklist_token_does_not_raise_when_redis_unreachable(monkeypatch):
    monkeypatch.setattr(token_blacklist, "_get_client", lambda: _BrokenRedis())

    token_blacklist.blacklist_token("header.payload.signature", exp=int(time.time()) + 60)

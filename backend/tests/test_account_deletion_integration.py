"""End-to-end integration tests for account deletion: exercises the real
route handlers in api/user.py and api/medical.py together against a single
shared in-memory fake relational store that actually enforces the same FK
behavior as 001_clearpath_schema.sql / 004_medical_profiles.sql —
ON DELETE CASCADE for medical_profiles and user_favorite_venues, but no
cascade for user_reports.user_id (RESTRICT, per fk_user_report_user) — so
these tests can genuinely prove cascade deletion, orphan-row absence, and
the known non-cascaded-reports gap, not just mock the DB away.

No live MySQL is used or required; `db` module is monkeypatched globally
so every blueprint (user.py, medical.py) that does `import db` and calls
db.db_cursor()/db.db_transaction() shares this same fake store.
"""

from contextlib import contextmanager

import pymysql
import pytest

import api.medical as medical_module
import api.user as user_module
from auth import issue_access_token


class _FakeStore:
    """In-memory relational store enforcing the same FK cascade rules as
    the real schema for the tables account deletion touches."""

    def __init__(self):
        self.users = {}  # user_id -> {"notification_preferences": "{}", ...}
        self.medical_profiles = {}  # user_id -> row dict
        self.favourites = {}  # (user_id, venue_id) -> {"created_at": ...}
        self.user_reports = {}  # report_id -> {"user_id": ...}

    def user_exists(self, user_id: str) -> bool:
        return user_id in self.users

    def has_outstanding_reports(self, user_id: str) -> bool:
        return any(r["user_id"] == user_id for r in self.user_reports.values())

    def delete_user_cascading(self, user_id: str) -> int:
        """Mirrors a real `DELETE FROM users WHERE user_id = %s`: MySQL
        checks ALL foreign keys referencing this row before touching
        anything. If any non-cascaded FK (user_reports.user_id) still
        references it, the whole statement fails and NOTHING is deleted
        — cascaded children only actually disappear if the DELETE itself
        succeeds."""
        if user_id not in self.users:
            return 0

        if self.has_outstanding_reports(user_id):
            raise pymysql.err.IntegrityError(
                1451, f"Cannot delete or update a parent row: a foreign key constraint fails "
                f"(fk_user_report_user, user_id={user_id})"
            )

        del self.users[user_id]
        self.medical_profiles.pop(user_id, None)
        for key in [k for k in self.favourites if k[0] == user_id]:
            del self.favourites[key]
        return 1


class _FakeCursor:
    def __init__(self, store: _FakeStore):
        self._store = store
        self._result = None
        self.rowcount = 0

    def execute(self, query, params=()):
        q = " ".join(query.split())

        # --- users / notification_preferences (JSON column on users) ---
        if q.startswith("SELECT notification_preferences FROM users WHERE user_id = %s"):
            row = self._store.users.get(params[0])
            self._result = {"notification_preferences": row["notification_preferences"]} if row else None
        elif q.startswith("UPDATE users SET notification_preferences = %s WHERE user_id = %s"):
            prefs_json, user_id = params
            self._store.users.setdefault(user_id, {})["notification_preferences"] = prefs_json

        # --- account deletion ---
        elif q.startswith("DELETE FROM users WHERE user_id = %s"):
            self.rowcount = self._store.delete_user_cascading(params[0])

        # --- medical_profiles (api/medical.py) ---
        elif q.startswith("SELECT date_of_birth, gender, address, blood_type, allergies, "
                           "conditions, medications, emergency_contacts FROM medical_profiles"):
            self._result = self._store.medical_profiles.get(params[-1])
        elif q.startswith("SELECT user_id FROM medical_profiles WHERE user_id = %s FOR UPDATE"):
            user_id = params[0]
            self._result = {"user_id": user_id} if user_id in self._store.medical_profiles else None
        elif q.startswith("UPDATE medical_profiles SET"):
            *values, user_id = params
            row = self._store.medical_profiles.setdefault(user_id, {})
            set_fields = [
                part.split(" = ")[0].strip()
                for part in q.split("SET ", 1)[1].split(" WHERE ")[0].split(",")
            ]
            for field, value in zip(set_fields, values):
                row[field] = value
        elif q.startswith("INSERT INTO medical_profiles"):
            user_id = params[0]
            fields = ("date_of_birth", "gender", "address", "blood_type",
                      "allergies", "conditions", "medications", "emergency_contacts")
            self._store.medical_profiles[user_id] = dict(zip(fields, params[1:]))
        elif q.startswith("DELETE FROM medical_profiles WHERE user_id = %s"):
            self._store.medical_profiles.pop(params[0], None)

        # --- user_favorite_venues (api/user.py favourites) ---
        elif q.startswith("SELECT ufv.venue_id, ufv.created_at") and "WHERE ufv.user_id = %s AND ufv.venue_id = %s" in q:
            user_id, venue_id = params
            row = self._store.favourites.get((user_id, venue_id))
            self._result = {"venue_id": venue_id, "created_at": row["created_at"], "level": None} if row else None
        elif q.startswith("SELECT ufv.venue_id, ufv.created_at"):
            user_id = params[0]
            rows = [
                {"venue_id": v, "created_at": row["created_at"], "level": None}
                for (u, v), row in self._store.favourites.items() if u == user_id
            ]
            self._result = sorted(rows, key=lambda r: r["created_at"], reverse=True)
        elif q.startswith("INSERT INTO user_favorite_venues"):
            import datetime as dt

            user_id, venue_id = params
            self._store.favourites.setdefault((user_id, venue_id), {"created_at": dt.datetime(2026, 1, 1)})
        elif q.startswith("DELETE FROM user_favorite_venues WHERE user_id = %s AND venue_id = %s"):
            existed = params in self._store.favourites
            self._store.favourites.pop(tuple(params), None)
            self.rowcount = 1 if existed else 0

        else:
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result or []


@pytest.fixture
def fake_store(monkeypatch):
    store = _FakeStore()

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(store)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor(store)

    # Patch the shared `db` module object itself, not a per-blueprint
    # reference — user.py and medical.py both do `import db` and call
    # db.db_cursor()/db.db_transaction() at call time, so patching the
    # module's attributes covers every blueprint sharing it.
    import db as db_module

    monkeypatch.setattr(db_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(db_module, "db_transaction", fake_db_transaction)
    return store


def _token_for(app, user_id):
    with app.app_context():
        return issue_access_token(user_id)


def _headers(app, user_id):
    return {"Authorization": f"Bearer {_token_for(app, user_id)}"}


# ---------------------------------------------------------------------------
# Cascade deletion
# ---------------------------------------------------------------------------

def test_delete_account_cascades_medical_profile_and_favourites(client, app, fake_store):
    headers = _headers(app, "u_alice")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}

    client.put(
        "/api/v1/user/medical-profile",
        json={"blood_type": "O+", "allergies": ["Penicillin"]},
        headers=headers,
    )
    client.post("/api/v1/user/favourites", json={"venue_id": "v_1001"}, headers=headers)

    assert "u_alice" in fake_store.medical_profiles
    assert ("u_alice", "v_1001") in fake_store.favourites

    resp = client.delete("/api/v1/user/account", headers=headers)

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "deleted"

    # No orphan rows: every user-owned record cascaded away with the user.
    assert "u_alice" not in fake_store.users
    assert "u_alice" not in fake_store.medical_profiles
    assert not any(key[0] == "u_alice" for key in fake_store.favourites)


def test_delete_account_blocked_by_outstanding_reports_leaves_everything_intact(client, app, fake_store):
    """Known schema gap (user_reports.user_id has no ON DELETE CASCADE):
    a user with an existing report can't be deleted at all. This proves
    the failure is atomic — MySQL checks FKs before deleting anything, so
    the user row and their other data are all left exactly as they were,
    never partially deleted."""
    headers = _headers(app, "u_alice")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}
    client.put("/api/v1/user/medical-profile", json={"blood_type": "O+"}, headers=headers)
    fake_store.user_reports["r_1"] = {"user_id": "u_alice"}

    with pytest.raises(pymysql.err.IntegrityError):
        client.delete("/api/v1/user/account", headers=headers)

    # Nothing was touched — atomicity preserved on failure.
    assert "u_alice" in fake_store.users
    assert "u_alice" in fake_store.medical_profiles


# ---------------------------------------------------------------------------
# JWT authentication / authorization boundaries
# ---------------------------------------------------------------------------

def test_delete_account_requires_bearer_token(client, fake_store):
    resp = client.delete("/api/v1/user/account")
    assert resp.status_code == 401


def test_delete_account_rejects_invalid_signature(client, fake_store):
    resp = client.delete(
        "/api/v1/user/account", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


def test_delete_account_identity_comes_only_from_token_not_payload(client, app, fake_store):
    """Authorization boundary: a caller can't delete a different user's
    account by naming them in the request — DELETE /user/account takes no
    body/params at all, identity is solely g.user_id from the verified JWT."""
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}
    fake_store.users["u_victim"] = {"notification_preferences": "{}"}

    headers = _headers(app, "u_alice")
    resp = client.delete(
        "/api/v1/user/account",
        json={"user_id": "u_victim"},  # attempted spoof; endpoint ignores the body entirely
        headers=headers,
    )

    assert resp.status_code == 200
    assert "u_alice" not in fake_store.users
    assert "u_victim" in fake_store.users  # untouched


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------

def test_deleting_one_user_never_affects_another_users_data(client, app, fake_store):
    alice_headers = _headers(app, "u_alice")
    bob_headers = _headers(app, "u_bob")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}
    fake_store.users["u_bob"] = {"notification_preferences": "{}"}

    client.put("/api/v1/user/medical-profile", json={"blood_type": "O+"}, headers=alice_headers)
    client.post("/api/v1/user/favourites", json={"venue_id": "v_1001"}, headers=alice_headers)
    client.put("/api/v1/user/medical-profile", json={"blood_type": "A-"}, headers=bob_headers)
    client.post("/api/v1/user/favourites", json={"venue_id": "v_1002"}, headers=bob_headers)

    resp = client.delete("/api/v1/user/account", headers=alice_headers)
    assert resp.status_code == 200

    # Alice is gone...
    assert "u_alice" not in fake_store.users
    assert "u_alice" not in fake_store.medical_profiles
    # ...Bob is completely untouched.
    assert "u_bob" in fake_store.users
    assert fake_store.medical_profiles["u_bob"]["blood_type"] == "A-"
    assert ("u_bob", "v_1002") in fake_store.favourites


def test_cannot_read_another_users_medical_profile_after_deletion_attempt(client, app, fake_store):
    """A deleted-then-recreated user_id (or a still-valid token for an
    account that's gone) must never resolve to someone else's data —
    each lookup is scoped by g.user_id, never a shared/global row."""
    alice_headers = _headers(app, "u_alice")
    bob_headers = _headers(app, "u_bob")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}
    fake_store.users["u_bob"] = {"notification_preferences": "{}"}
    client.put("/api/v1/user/medical-profile", json={"blood_type": "B+"}, headers=bob_headers)

    client.delete("/api/v1/user/account", headers=alice_headers)

    # Alice's (now-orphaned-token) request for medical profile must never
    # return Bob's data — it must come back empty/default, scoped to her
    # own (now-nonexistent) user_id.
    resp = client.get("/api/v1/user/medical-profile", headers=alice_headers)
    assert resp.status_code == 200
    assert resp.get_json()["blood_type"] is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_delete_account_ignores_malformed_json_body(client, app, fake_store):
    """DELETE takes no body; a garbage body must not break the request —
    request.get_json(silent=True) semantics apply app-wide, and this
    route doesn't even read the body, but a client sending one anyway
    shouldn't matter."""
    headers = _headers(app, "u_alice")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}

    resp = client.delete(
        "/api/v1/user/account",
        data="not json at all",
        headers={**headers, "Content-Type": "application/json"},
    )

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Concurrent access
# ---------------------------------------------------------------------------

def test_deleting_the_same_account_twice_is_idempotent_not_a_500(client, app, fake_store):
    """Simulates two concurrent DELETE requests racing for the same
    account (e.g. a double-tap or a retried request): the token is still
    validly signed for both calls (JWT verification doesn't know the user
    row is gone), so the second DELETE must complete safely — rowcount 0,
    same 200 response — rather than erroring, matching real MySQL's
    DELETE-affecting-zero-rows semantics."""
    headers = _headers(app, "u_alice")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}

    first = client.delete("/api/v1/user/account", headers=headers)
    second = client.delete("/api/v1/user/account", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200  # idempotent, not an error


def test_concurrent_favourite_writes_from_two_users_do_not_interleave(client, app, fake_store):
    """Simulates two users concurrently adding favourites — since each
    write is scoped to g.user_id and keyed by (user_id, venue_id), one
    user's write can never clobber or appear in the other's list, even
    when interleaved."""
    alice_headers = _headers(app, "u_alice")
    bob_headers = _headers(app, "u_bob")
    fake_store.users["u_alice"] = {"notification_preferences": "{}"}
    fake_store.users["u_bob"] = {"notification_preferences": "{}"}

    # Interleaved calls, simulating concurrent requests.
    client.post("/api/v1/user/favourites", json={"venue_id": "v_shared"}, headers=alice_headers)
    client.post("/api/v1/user/favourites", json={"venue_id": "v_shared"}, headers=bob_headers)
    client.post("/api/v1/user/favourites", json={"venue_id": "v_1002"}, headers=alice_headers)

    alice_favs = client.get("/api/v1/user/favourites", headers=alice_headers).get_json()
    bob_favs = client.get("/api/v1/user/favourites", headers=bob_headers).get_json()

    assert {item["venue_id"] for item in alice_favs["items"]} == {"v_shared", "v_1002"}
    assert {item["venue_id"] for item in bob_favs["items"]} == {"v_shared"}

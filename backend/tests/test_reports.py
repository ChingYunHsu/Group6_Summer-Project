"""Tests for the DB-backed Reports API (SOP 4 + SOP 1 + SOP 2 BE-side).

The MySQL layer is faked via a cursor that simulates user_reports +
report_confirmations, so these run without a live database. Auth uses real
signed JWTs via issue_access_token (g.user_id), matching the bearer-auth gate
applied to submit/confirm.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

import api.reports as reports_module
from auth import issue_access_token

SUBMIT_URL = "/api/v1/reports"
LIST_URL = "/api/v1/reports"


def _confirm_url(report_id):
    return f"/api/v1/reports/{report_id}/confirmations"


# ---------------------------------------------------------------------------
# Fake DB
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Minimal cursor emulating user_reports + report_confirmations.

    Recognizes the exact SQL emitted by reports.py (normalized whitespace)
    and maintains an in-memory store so FK/UNIQUE semantics + action rules
    are exercised faithfully.
    """

    def __init__(self, reports: dict, confirmations: list, categories: set):
        self._reports = reports
        self._confirmations = confirmations
        self._categories = categories
        self._result = None
        self._rowcount = 0

    def execute(self, query, params=()):
        q = " ".join(query.split())

        if q.startswith("SELECT 1 FROM report_categories"):
            self._result = (1,) if params[0] in self._categories else None

        elif q.startswith("INSERT INTO user_reports"):
            (report_id, user_id, venue_id, issue_type, lat, lng, accuracy,
             anonymous, description, photos, reported_by, status,
             expires_in_minutes, default_lang, fallback_lang, _exp) = params
            self._reports[report_id] = {
                "report_id": report_id, "user_id": user_id, "venue_id": venue_id,
                "issue_type": issue_type, "latitude": lat, "longitude": lng,
                "accuracy_meters": accuracy, "anonymous": anonymous,
                "description": description, "photos": photos, "status": status,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
                "expires_in_minutes": expires_in_minutes,
            }
            self._result = None
            self._rowcount = 1

        elif q.startswith("SELECT report_id, user_id, venue_id, issue_type") and "WHERE report_id = %s" in q and "FROM user_reports ur" not in q:
            # single-row re-read after insert (DictCursor → dict)
            self._result = self._row_to_select_dict(self._reports.get(params[0]))

        elif q.startswith("SELECT ur.report_id") and "WHERE ur.status = %s" in q:
            # list active
            self._result = [self._row_with_aggregate(r)
                            for r in self._reports.values() if r["status"] == params[0]]

        elif (
            q.startswith(
                "SELECT venue_id, issue_type, status, expires_at "
                "FROM user_reports WHERE report_id = %s"
            )
        ):
            r = self._reports.get(params[0])
            self._result = {
                "venue_id": r["venue_id"],
                "issue_type": r["issue_type"],
                "status": r["status"],
                "expires_at": r["expires_at"],
            } if r else None
        
        elif q.startswith("INSERT INTO report_confirmations"):
            (report_id, user_id, action, language, _ctx) = params
            existing = next(
                (c for c in self._confirmations
                 if c["report_id"] == report_id and c["user_id"] == user_id),
                None,
            )
            if existing:
                existing["action"] = action
                existing["created_at"] = datetime.now(timezone.utc)
                self._rowcount = 2  # ON DUPLICATE KEY UPDATE reports 2
            else:
                self._confirmations.append({
                    "report_id": report_id, "user_id": user_id, "action": action,
                    "created_at": datetime.now(timezone.utc),
                })
                self._rowcount = 1

        elif q.startswith("UPDATE user_reports SET status = %s WHERE report_id = %s AND status = %s"):
            # resolved
            new_status, report_id, cur_status = params
            r = self._reports.get(report_id)
            if r and r["status"] == cur_status:
                r["status"] = new_status
                self._rowcount = 1
            else:
                self._rowcount = 0

        elif q.startswith("UPDATE user_reports SET expires_at = DATE_ADD"):
            # still_here TTL extend
            minutes, report_id, cur_status = params
            r = self._reports.get(report_id)
            if r and r["status"] == cur_status:
                r["expires_at"] = r["expires_at"] + timedelta(minutes=minutes)
                r["expires_in_minutes"] = r.get("expires_in_minutes", 0) + minutes
                self._rowcount = 1
            else:
                self._rowcount = 0

        elif q.startswith("SELECT ur.report_id") and "WHERE ur.report_id = %s" in q:
            # confirm re-read single report
            r = self._reports.get(params[0])
            self._result = self._row_with_aggregate(r) if r else None

        elif q.startswith("UPDATE user_reports SET status = %s WHERE status = %s AND expires_at <= NOW()"):
            # cleanup_expired_reports
            new_status, cur_status = params
            count = 0
            now = datetime.now(timezone.utc)
            for r in self._reports.values():
                if r["status"] == cur_status and r["expires_at"] <= now:
                    r["status"] = new_status
                    count += 1
            self._rowcount = count

        else:
            raise AssertionError(f"unexpected SQL: {q!r}")

    def _row_to_select_dict(self, r):
        if r is None:
            return None
        return {
            "report_id": r["report_id"], "user_id": r["user_id"],
            "venue_id": r["venue_id"], "issue_type": r["issue_type"],
            "latitude": r["latitude"], "longitude": r["longitude"],
            "accuracy_meters": r["accuracy_meters"], "anonymous": r["anonymous"],
            "description": r["description"], "photos": r["photos"],
            "status": r["status"], "created_at": r["created_at"],
            "expires_at": r["expires_at"],
        }

    def _row_with_aggregate(self, r):
        if r is None:
            return None
        confs = [c for c in self._confirmations if c["report_id"] == r["report_id"]]
        latest = max(confs, key=lambda c: c["created_at"]) if confs else None
        return {
            "report_id": r["report_id"], "user_id": r["user_id"],
            "venue_id": r["venue_id"], "issue_type": r["issue_type"],
            "latitude": r["latitude"], "longitude": r["longitude"],
            "accuracy_meters": r["accuracy_meters"], "anonymous": r["anonymous"],
            "description": r["description"], "photos": r["photos"],
            "status": r["status"], "created_at": r["created_at"],
            "expires_at": r["expires_at"],
            "confirmation_count": len(confs),
            "latest_action": latest["action"] if latest else None,
            "latest_action_at": latest["created_at"] if latest else None,
        }

    @property
    def rowcount(self):
        return self._rowcount

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result or []

    def close(self):
        pass


class _FakeConn:
    def __init__(self, store):
        self._store = store

    def cursor(self):
        return _FakeCursor(self._store["reports"], self._store["confirmations"],
                           self._store["categories"])

    def close(self):
        pass


@contextmanager
def _fake_cursor(store):
    yield _FakeCursor(store["reports"], store["confirmations"], store["categories"])


@contextmanager
def _fake_transaction(store):
    yield _FakeCursor(store["reports"], store["confirmations"], store["categories"])


@pytest.fixture
def fake_db(monkeypatch):
    store = {
        "reports": {},
        "confirmations": [],
        "categories": {"elevator_broken", "large_crowd", "toilet_out_of_order"},
    }

    monkeypatch.setattr(
        reports_module,
        "_sync_accessibility_warning",
        lambda cursor, venue_id: None,
    )
    
    class _DbStub:
        db_cursor = lambda self: _fake_cursor(store)
        db_transaction = lambda self: _fake_transaction(store)

    monkeypatch.setattr(reports_module, "_db", lambda: _DbStub())
    return store


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = issue_access_token("u_1001")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def test_submit_path_a_venue_bound_persists(fake_db, client, auth_headers):
    resp = client.post(SUBMIT_URL, json={
        "issue_type": "elevator_broken",
        "venue_id": "v_1001",
        "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["report_scope"] == "venue_bound"
    assert data["status"] == "active"
    assert data["issue_type_label"] == "Lift Broken"
    assert data["confirmations"]["count"] == 0
    assert data["expires_at"] is not None
    # row actually landed in the fake store
    assert len(fake_db["reports"]) == 1


def test_submit_path_b_standalone_has_null_venue(fake_db, client, auth_headers):
    resp = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd",
        "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers)

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["report_scope"] == "standalone"
    assert data["venue_id"] is None
    # stored row has NULL venue_id (Path B reuses user_reports per DB-1)
    rid = data["report_id"]
    assert fake_db["reports"][rid]["venue_id"] is None


def test_submit_rejects_invalid_issue_type(fake_db, client, auth_headers):
    resp = client.post(SUBMIT_URL, json={
        "issue_type": "nope",
        "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers)

    assert resp.status_code == 400
    assert resp.get_json()["invalid_fields"] == ["issue_type"]


def test_submit_rejects_missing_fields(fake_db, client, auth_headers):
    resp = client.post(SUBMIT_URL, json={"issue_type": "large_crowd"}, headers=auth_headers)
    assert resp.status_code == 400
    assert set(resp.get_json()["missing_fields"]) == {"latitude", "longitude"}


def test_submit_requires_bearer_token(fake_db, client):
    resp = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def test_list_returns_only_active_reports(fake_db, client, auth_headers):
    # one active, one resolved
    for i, status in enumerate(["active", "resolved"]):
        client.post(SUBMIT_URL, json={
            "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
        }, headers=auth_headers)
        if status == "resolved":
            # flip the last inserted to resolved via confirmation
            rids = list(fake_db["reports"].keys())
            client.post(_confirm_url(rids[-1]), json={"action": "resolved"},
                        headers=auth_headers)

    resp = client.get(LIST_URL, headers={"X-API-Key": "dev-api-key"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "db"
    assert data["count"] == 1
    assert data["items"][0]["status"] == "active"


# ---------------------------------------------------------------------------
# Confirmations
# ---------------------------------------------------------------------------

def test_confirm_still_here_extends_ttl(fake_db, client, auth_headers):
    rid = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    before = fake_db["reports"][rid]["expires_at"]

    resp = client.post(_confirm_url(rid), json={"action": "still_here"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "confirmed"
    after = fake_db["reports"][rid]["expires_at"]
    assert after > before  # TTL extended by +30 min


def test_confirm_resolved_sets_status(fake_db, client, auth_headers):
    rid = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]

    resp = client.post(_confirm_url(rid), json={"action": "resolved"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "resolved"
    assert fake_db["reports"][rid]["status"] == "resolved"


def test_confirm_is_idempotent_per_user(fake_db, client, auth_headers):
    """Same user confirming twice produces ONE confirmation row (uq_report_user)."""
    rid = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]

    client.post(_confirm_url(rid), json={"action": "still_here"}, headers=auth_headers)
    client.post(_confirm_url(rid), json={"action": "still_here"}, headers=auth_headers)

    user_confs = [c for c in fake_db["confirmations"] if c["report_id"] == rid]
    assert len(user_confs) == 1  # no duplicate row


def test_confirm_404_for_unknown_report(fake_db, client, auth_headers):
    resp = client.post(_confirm_url("does-not-exist"),
                       json={"action": "still_here"}, headers=auth_headers)
    assert resp.status_code == 404


def test_confirm_rejects_invalid_action(fake_db, client, auth_headers):
    rid = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    resp = client.post(_confirm_url(rid), json={"action": "bogus"}, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.get_json()["missing_fields"] == ["action"]


# ---------------------------------------------------------------------------
# TTL cleanup (SOP 2)
# ---------------------------------------------------------------------------

def test_cleanup_soft_expires_only_active_overdue(fake_db, client, auth_headers):
    # active, not yet expired
    rid_active = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    # active, already expired (force expires_at into the past)
    rid_overdue = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    fake_db["reports"][rid_overdue]["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)
    # resolved (should NOT be touched even if its expires_at is past)
    rid_resolved = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    client.post(_confirm_url(rid_resolved), json={"action": "resolved"}, headers=auth_headers)
    fake_db["reports"][rid_resolved]["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)

    expired = reports_module.cleanup_expired_reports()

    assert expired == 1
    assert fake_db["reports"][rid_active]["status"] == "active"
    assert fake_db["reports"][rid_overdue]["status"] == "expired"
    assert fake_db["reports"][rid_resolved]["status"] == "resolved"  # untouched


def test_cleanup_is_idempotent(fake_db, client, auth_headers):
    rid = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers).get_json()["report_id"]
    fake_db["reports"][rid]["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)

    assert reports_module.cleanup_expired_reports() == 1
    assert reports_module.cleanup_expired_reports() == 0  # second run no-op


# ---------------------------------------------------------------------------
# Fallback: mock path when no DB
# ---------------------------------------------------------------------------

def test_submit_falls_back_to_mock_without_db(client, auth_headers, monkeypatch):
    monkeypatch.setattr(reports_module, "_db", lambda: None)
    resp = client.post(SUBMIT_URL, json={
        "issue_type": "large_crowd", "latitude": 40.71, "longitude": -73.99,
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["data_mode"] == "mock"

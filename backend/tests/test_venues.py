"""Unit tests for the DB-backed venues list/detail endpoints with MySQL faked
out, so this runs without a live database."""

from contextlib import contextmanager

import pytest

import api.venues as venues_module


ROWS = [
    {
        "venue_id": "venue_a",
        "name": "Venue A",
        "venue_type": "hospital",
        "accessible_status": "full_access",
        "open_now": 1,
        "language_tags": '["EN", "FR"]',
        "accessibility_features": "[]",
        "supported_services": '["French Help Available"]',
        "opening_hours_structured": None,
        "chatbot_enabled": 1,
        "wheelchair_friendly": 1,
        "step_free_route": 1,
        "accessible_toilet": 1,
        "created_at": None,
    },
    {
        "venue_id": "venue_b",
        "name": "Venue B",
        "venue_type": "pharmacy",
        "accessible_status": "no_access",
        "open_now": 0,
        "language_tags": '["EN"]',
        "accessibility_features": "[]",
        "supported_services": "[]",
        "opening_hours_structured": None,
        "chatbot_enabled": 0,
        "wheelchair_friendly": 0,
        "step_free_route": 0,
        "accessible_toilet": 0,
        "created_at": None,
    },
    {
        "venue_id": "venue_unknown",
        "name": "Venue with unverified accessibility",
        "venue_type": "clinic",
        "accessible_status": "unknown",
        "open_now": 1,
        "language_tags": '["es"]',
        "accessibility_features": "[]",
        "supported_services": "[]",
        "opening_hours_structured": None,
        "chatbot_enabled": 0,
        "wheelchair_friendly": 0,
        "step_free_route": 0,
        "accessible_toilet": 0,
        "created_at": None,
    },
]


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())
        if query.startswith("SELECT * FROM venues WHERE venue_id"):
            self._result = next((r for r in self._rows if r["venue_id"] == params[0]), None)
            return
        if not query.startswith("SELECT * FROM venues"):
            raise AssertionError(f"Unexpected query in fake cursor: {query!r}")

        rows = list(self._rows)
        param_iter = iter(params)
        if "accessible_status = %s" in query:
            value = next(param_iter)
            rows = [r for r in rows if r["accessible_status"] == value]
        elif "accessible_status IN (%s, %s, %s)" in query:
            values = {next(param_iter), next(param_iter), next(param_iter)}
            rows = [r for r in rows if r["accessible_status"] in values]
        elif "accessible_status != %s" in query:
            value = next(param_iter)
            rows = [r for r in rows if r["accessible_status"] != value]
        if "open_now = %s" in query:
            value = next(param_iter)
            rows = [r for r in rows if r["open_now"] == value]
        if "venue_type = %s" in query:
            value = next(param_iter)
            rows = [r for r in rows if r["venue_type"] == value]
        self._result = rows

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result


@pytest.fixture
def fake_venues_db(monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(ROWS)

    monkeypatch.setattr(venues_module, "db_cursor", fake_db_cursor)


def test_list_venues_filters_by_language(client, fake_venues_db):
    resp = client.get("/api/v1/venues?languages=FR", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 1
    assert body["items"][0]["venue_id"] == "venue_a"


def test_list_venues_filters_by_accessible_and_open_now(client, fake_venues_db):
    resp = client.get(
        "/api/v1/venues?accessible=true&open_now=true", headers={"X-API-Key": "test"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert [item["venue_id"] for item in body["items"]] == ["venue_a"]


def test_list_venues_does_not_treat_unknown_as_not_accessible(client, fake_venues_db):
    resp = client.get("/api/v1/venues?accessible=false", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    assert "venue_unknown" not in {item["venue_id"] for item in resp.get_json()["items"]}


def test_list_venues_normalises_lass_language_codes(client, fake_venues_db):
    resp = client.get("/api/v1/venues?languages=ES", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    assert [item["venue_id"] for item in resp.get_json()["items"]] == ["venue_unknown"]
    assert resp.get_json()["items"][0]["language_tags"] == ["ES"]


def test_list_venues_rejects_unknown_venue_type(client, fake_venues_db):
    resp = client.get("/api/v1/venues?venue_type=bogus", headers={"X-API-Key": "test"})
    assert resp.status_code == 400


def test_list_venues_extracts_bilingual_badges(client, fake_venues_db):
    resp = client.get("/api/v1/venues", headers={"X-API-Key": "test"})
    body = resp.get_json()
    venue_a = next(item for item in body["items"] if item["venue_id"] == "venue_a")
    assert venue_a["bilingual_service_badges"] == [
        {"label": "French Help Available", "language": "French"}
    ]

    venue_b = next(item for item in body["items"] if item["venue_id"] == "venue_b")
    assert venue_b["bilingual_service_badges"] == []


def test_get_venue_by_id_from_db(client, fake_venues_db):
    resp = client.get("/api/v1/venues/venue_a", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    assert resp.get_json()["venue_id"] == "venue_a"

"""Explicit coverage of the venues list endpoint's query-param filtering
mechanics (languages / accessible / open_now) against the mock dataset.

list_venues() tries the real venues table first and only falls back to
mock data on any DB error, so these tests force that fallback by making
db_cursor raise — otherwise they'd be flaky against an environment that
happens to have a real (possibly empty) `venues` table reachable."""

import pytest

import api.venues as venues_module
from mock_data import VENUES


@pytest.fixture(autouse=True)
def force_mock_fallback(monkeypatch):
    def _raise():
        raise RuntimeError("no DB in this test")

    monkeypatch.setattr(venues_module, "db_cursor", _raise)


def test_language_filter_matches_only_supported_languages(client):
    resp = client.get("/api/v1/venues?languages=ES")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] > 0
    assert all("ES" in venue["language_tags"] for venue in body["items"])


def test_accessible_filter_true_returns_only_full_access(client):
    resp = client.get("/api/v1/venues?accessible=true")
    body = resp.get_json()
    assert all(venue["accessible_status"] == "full_access" for venue in body["items"])


def test_accessible_filter_false_excludes_full_access(client):
    resp = client.get("/api/v1/venues?accessible=false")
    body = resp.get_json()
    assert all(venue["accessible_status"] != "full_access" for venue in body["items"])


def test_open_now_filter_true_returns_only_open_venues(client):
    resp = client.get("/api/v1/venues?open_now=true")
    body = resp.get_json()
    assert all(venue["open_now"] is True for venue in body["items"])


def test_combined_filters_are_applied_together(client):
    resp = client.get("/api/v1/venues?accessible=true&open_now=true&languages=EN")
    body = resp.get_json()
    for venue in body["items"]:
        assert venue["accessible_status"] == "full_access"
        assert venue["open_now"] is True
        assert "EN" in venue["language_tags"]


def test_no_filters_returns_full_mock_dataset(client):
    resp = client.get("/api/v1/venues")
    assert resp.get_json()["count"] == len(VENUES)

"""Locks in the OpenAPI InsightsDashboard schema contract for the DB-backed
path: quick_triage and fastest_hubs[].travel_minutes must always be present
(openapi.yaml requires both), matching what the mock fallback already
returns."""

import api.insights as insights_module
from api.insights import _quick_triage, _travel_minutes_by_venue


def test_quick_triage_picks_lowest_wait_hub():
    hubs = [
        {"venue_id": "v_slow", "venue_name": "Slow Clinic", "wait_minutes": 20},
        {"venue_id": "v_fast", "venue_name": "Fast Clinic", "wait_minutes": 5},
    ]
    result = _quick_triage(hubs)
    assert result == {"wait_minutes": 5, "label": "Fast Clinic", "venue_name": "Fast Clinic"}


def test_quick_triage_ignores_hubs_with_no_data():
    hubs = [{"venue_id": "v_nodata", "venue_name": "No Data", "wait_minutes": None}]
    result = _quick_triage(hubs)
    assert result["venue_name"] is None
    assert result["wait_minutes"] == 0


def test_quick_triage_empty_hubs_returns_placeholder():
    assert _quick_triage([])["venue_name"] is None


def test_travel_minutes_by_venue_returns_empty_without_origin():
    class _Cursor:
        def execute(self, *a, **k):
            raise AssertionError("should not query without an origin")

    assert _travel_minutes_by_venue(_Cursor(), ["v1"], None, None) == {}


def test_travel_minutes_by_venue_computes_distance():
    class _Cursor:
        def execute(self, query, params=()):
            self.executed = (query, params)

        def fetchall(self):
            # ~1 degree of latitude ≈ 111km apart from the origin
            return [("v1", 41.0, -73.0)]

    cur = _Cursor()
    result = _travel_minutes_by_venue(cur, ["v1"], 40.0, -73.0)
    assert result["v1"] > 0
    assert isinstance(result["v1"], int)


def test_get_insights_db_path_includes_quick_triage_and_travel_minutes(client, monkeypatch):
    class _FakeCursor:
        def __init__(self):
            self.step = 0

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=()):
            q = " ".join(query.split())
            self.last_query = q

        def fetchone(self):
            return ("MN05",)

        def fetchall(self):
            if "FROM busyness_scores bs" in self.last_query:
                return [(40, 10)]
            if "FROM busyness_forecasts bf" in self.last_query:
                return []
            if "LEFT JOIN busyness_scores bs ON bs.venue_id = v.venue_id" in self.last_query:
                return [("v1", "Test Venue", "[]", "full_access", 40, "moderate", 10)]
            if "FROM venues WHERE venue_id IN" in self.last_query:
                return [("v1", 40.71, -73.99)]
            return []

    class _FakeConn:
        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(insights_module, "_get_db_conn", lambda: _FakeConn())

    resp = client.get("/api/v1/insights?district=MN05&lat=40.70&lon=-73.98", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["data_mode"] == "db"
    assert "quick_triage" in data
    assert data["quick_triage"]["venue_name"] == "Test Venue"
    assert data["fastest_hubs"][0]["travel_minutes"] is not None
    assert isinstance(data["fastest_hubs"][0]["travel_minutes"], int)

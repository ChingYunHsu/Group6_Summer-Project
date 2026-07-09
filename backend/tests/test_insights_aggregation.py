"""Tests for area aggregation logic (D3.5 / D3.7).

Covers _real_time_density, _best_travel_window, _fastest_hubs,
_prediction_series, and the get_insights endpoint mock fallback.

Run: python -m pytest backend/tests/test_insights_aggregation.py -v
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

import api.insights as insights_module


# ---------------------------------------------------------------------------
# Fake cursor for aggregation queries
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Simulates MySQL cursor results for insights aggregation queries."""

    def __init__(self, store: dict):
        self._store = store
        self._result = None

    def execute(self, query, params=()):
        q = " ".join(query.split())

        if "FROM busyness_scores bs" in q and "JOIN venues v" in q and "v.district = %s" in q:
            district = params[0]
            rows = []
            for v in self._store.get("venues", []):
                if v.get("district") != district:
                    continue
                scores = self._store.get("busyness_scores", {}).get(v["venue_id"], [])
                for s in scores:
                    rows.append((s["score"], s.get("wait", 0)))
            self._result = rows

        elif "FROM busyness_forecasts bf" in q and "JOIN venues v" in q and "v.district = %s" in q:
            district = params[0]
            by_hour = {}
            for v in self._store.get("venues", []):
                if v.get("district") != district:
                    continue
                forecasts = self._store.get("busyness_forecasts", {}).get(v["venue_id"], [])
                for f in forecasts:
                    ff = f["forecast_for"]
                    by_hour.setdefault(ff, []).append(f["predicted_score"])
            rows = [(hour, sum(scores) / len(scores)) for hour, scores in sorted(by_hour.items())]
            if "LIMIT 12" in q:
                rows = rows[:12]
            self._result = rows

        elif "LEFT JOIN busyness_scores bs ON bs.venue_id = v.venue_id" in q:
            district = params[0]
            limit = params[1]
            rows = []
            for v in self._store.get("venues", []):
                if v.get("district") != district:
                    continue
                scores = self._store.get("busyness_scores", {}).get(v["venue_id"], [])
                if scores:
                    latest = max(scores, key=lambda s: s.get("created_at", datetime.min))
                    rows.append((v["venue_id"], v["name"], v.get("language_tags"),
                                 v.get("accessible_status"), latest["score"],
                                 latest.get("level"), latest.get("wait")))
                else:
                    rows.append((v["venue_id"], v["name"], v.get("language_tags"),
                                 v.get("accessible_status"), None, None, None))
            rows.sort(key=lambda r: (
                100 if r[4] is None else r[4],
                999 if r[6] is None else r[6],
            ))
            self._result = rows[:limit]

        elif "SELECT DISTINCT district FROM venues" in q:
            districts = sorted(set(
                v["district"] for v in self._store.get("venues", [])
                if v.get("district")
            ))
            self._result = [(districts[0],)] if districts else None

        else:
            self._result = []

    def fetchone(self):
        return self._result[0] if isinstance(self._result, list) and self._result else self._result

    def fetchall(self):
        return self._result if self._result else []

    def close(self):
        pass


class _FakeConn:
    def __init__(self, store):
        self._store = store

    def cursor(self):
        return _FakeCursor(self._store)

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Shared test store
# ---------------------------------------------------------------------------

def _make_store(district="MN05", num_venues=3):
    now = datetime.now(timezone.utc)
    venues = []
    scores = {}
    forecasts = {}

    for i in range(num_venues):
        vid = f"v_test_{i + 1}"
        venues.append({
            "venue_id": vid,
            "name": f"Test Venue {i + 1}",
            "district": district,
            "language_tags": json.dumps(["EN", "ES"] if i == 0 else ["EN"]),
            "accessible_status": "full_access" if i == 0 else "partial",
        })
        scores[vid] = [{
            "score": 30 + i * 20,
            "level": "quiet" if i == 0 else ("moderate" if i == 1 else "busy"),
            "wait": 5 + i * 5,
            "created_at": now - timedelta(minutes=1),
        }]
        forecasts[vid] = [
            {"forecast_for": now + timedelta(hours=h + 1), "predicted_score": 25 + h * 10 + i * 5}
            for h in range(3)
        ]

    return {
        "venues": venues,
        "busyness_scores": scores,
        "busyness_forecasts": forecasts,
    }


# ---------------------------------------------------------------------------
# D3.5: _real_time_density
# ---------------------------------------------------------------------------

def test_density_empty_district_returns_zero():
    store = {"venues": [], "busyness_scores": {}, "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "NONEXISTENT")
    assert result["percent"] == 0
    assert "no data" in result["trend"]


def test_density_single_venue():
    store = _make_store("MN05", num_venues=1)
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 30


def test_density_multi_venue_average():
    store = _make_store("MN05", num_venues=3)
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 50


def test_density_different_district_not_included():
    store = _make_store("MN05", num_venues=2)
    store["venues"].append({
        "venue_id": "v_bk_1", "name": "BK Venue", "district": "BK02",
        "language_tags": "[]", "accessible_status": "none",
    })
    store["busyness_scores"]["v_bk_1"] = [{
        "score": 90, "level": "busy", "wait": 20,
        "created_at": datetime.now(),
    }]
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 40


# ---------------------------------------------------------------------------
# D3.5: _best_travel_window
# ---------------------------------------------------------------------------

def test_travel_window_empty_returns_placeholder():
    store = {"venues": [], "busyness_scores": {}, "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "NONEXISTENT")
    assert result["start_time"] is None
    assert result["cta_label"] == "Check back soon"


def test_travel_window_picks_lowest_2hour_window():
    store = _make_store("MN05", num_venues=1)
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] is not None
    assert result["end_time"] is not None
    assert result["cta_label"] == "Plan Route"


def test_travel_window_cross_venue_average():
    store = _make_store("MN05", num_venues=2)
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] is not None
    assert result["end_time"] is not None


def test_travel_window_single_hour_fallback():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05"}],
        "busyness_scores": {},
        "busyness_forecasts": {
            "v1": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] == result["end_time"]


# ---------------------------------------------------------------------------
# D3.5: _fastest_hubs
# ---------------------------------------------------------------------------

def test_hubs_empty_district():
    store = {"venues": [], "busyness_scores": {}, "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "NONEXISTENT")
    assert result == []


def test_hubs_single_venue():
    store = _make_store("MN05", num_venues=1)
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")
    assert len(result) == 1
    assert result[0]["venue_id"] == "v_test_1"
    assert result[0]["flow_status"] == "OPTIMAL FLOW"


def test_hubs_ranked_by_score_then_wait():
    store = _make_store("MN05", num_venues=3)
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")
    assert len(result) == 3
    assert result[0]["venue_id"] == "v_test_1"
    assert result[1]["venue_id"] == "v_test_2"
    assert result[2]["venue_id"] == "v_test_3"


def test_hubs_flow_status_levels():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v_low", "name": "Low", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
            {"venue_id": "v_mid", "name": "Mid", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
            {"venue_id": "v_high", "name": "High", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
        ],
        "busyness_scores": {
            "v_low": [{"score": 20, "level": "quiet", "wait": 3, "created_at": now}],
            "v_mid": [{"score": 55, "level": "moderate", "wait": 10, "created_at": now}],
            "v_high": [{"score": 85, "level": "busy", "wait": 25, "created_at": now}],
        },
        "busyness_forecasts": {},
    }
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")
    assert result[0]["flow_status"] == "OPTIMAL FLOW"
    assert result[1]["flow_status"] == "MODERATE"
    assert result[2]["flow_status"] == "DIVERTING"


def test_hubs_no_score_venue_still_listed():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v_scored", "name": "Scored", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
            {"venue_id": "v_nodata", "name": "NoData", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
        ],
        "busyness_scores": {
            "v_scored": [{"score": 40, "level": "moderate", "wait": 8, "created_at": now}],
        },
        "busyness_forecasts": {},
    }
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")
    assert len(result) == 2
    assert result[0]["venue_id"] == "v_scored"
    assert result[1]["venue_id"] == "v_nodata"
    assert result[1]["flow_status"] == "NO DATA"


def test_hubs_respects_limit():
    store = _make_store("MN05", num_venues=5)
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05", limit=2)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# D3.5: _prediction_series
# ---------------------------------------------------------------------------

def test_prediction_series_empty():
    store = {"venues": [], "busyness_scores": {}, "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "NONEXISTENT")
    assert result == []


def test_prediction_series_averages_cross_venue():
    store = _make_store("MN05", num_venues=2)
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "MN05")
    assert len(result) == 3
    assert result == [28, 38, 48]


# ---------------------------------------------------------------------------
# get_insights endpoint — mock fallback
# ---------------------------------------------------------------------------

def test_get_insights_mock_fallback(client, monkeypatch):
    """When no DB is reachable, the endpoint falls back to mock_data."""
    monkeypatch.setattr(insights_module, "_get_db_conn",
                        lambda: (_ for _ in ()).throw(RuntimeError("no DB")))
    resp = client.get("/api/v1/insights", headers={"X-API-Key": "dev-api-key"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "mock"
    assert "real_time_density" in data
    assert "best_travel_window" in data
    assert "fastest_hubs" in data
    assert isinstance(data["fastest_hubs"], list)


def test_get_insights_mock_supports_district_param(client):
    resp = client.get("/api/v1/insights?district=MN05",
                      headers={"X-API-Key": "dev-api-key"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["district"] == "MN05"
    assert data["data_mode"] in ("db", "mock")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_density_tie_break():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v_a", "name": "A", "district": "MN05"},
            {"venue_id": "v_b", "name": "B", "district": "MN05"},
        ],
        "busyness_scores": {
            "v_a": [{"score": 50, "level": "moderate", "wait": 10, "created_at": now}],
            "v_b": [{"score": 50, "level": "moderate", "wait": 10, "created_at": now}],
        },
        "busyness_forecasts": {},
    }
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 50


def test_hubs_tie_break_by_wait():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v_fast", "name": "Fast", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
            {"venue_id": "v_slow", "name": "Slow", "district": "MN05",
             "language_tags": "[]", "accessible_status": "none"},
        ],
        "busyness_scores": {
            "v_fast": [{"score": 50, "level": "moderate", "wait": 5, "created_at": now}],
            "v_slow": [{"score": 50, "level": "moderate", "wait": 15, "created_at": now}],
        },
        "busyness_forecasts": {},
    }
    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")
    assert result[0]["venue_id"] == "v_fast"
    assert result[1]["venue_id"] == "v_slow"


def test_prediction_series_all_venues_same_forecast():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v1", "name": "V1", "district": "MN05"},
            {"venue_id": "v2", "name": "V2", "district": "MN05"},
        ],
        "busyness_scores": {},
        "busyness_forecasts": {
            "v1": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
            "v2": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "MN05")
    assert result == [40]

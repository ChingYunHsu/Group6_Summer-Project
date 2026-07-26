"""Tests for area aggregation logic (D3.5 / D3.7).

Covers _real_time_density, _best_travel_window, _fastest_hubs,
_prediction_series, and the get_insights endpoint mock fallback.

Sprint 5 SOP: _real_time_density and _fastest_hubs are V2-only now, same as
the single-venue busyness endpoints in venues.py — only clinic/hospital/
pharmacy venues are considered, resolved from each venue's nearest future
forecast-v2 row. AED/restroom must never appear, even though historical V2
rows exist for them (the SOP explicitly calls this out as not assumable
from historic data).

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

        if "v.venue_type IN" in q:
            # _eligible_venues_in_district: venue_id/name/language_tags/
            # accessible_status for clinic/hospital/pharmacy in district.
            district = params[0]
            eligible_types = set(params[1:])
            rows = [
                (v["venue_id"], v["name"], v.get("language_tags"), v.get("accessible_status"))
                for v in self._store.get("venues", [])
                if v.get("district") == district and v.get("venue_type", "clinic") in eligible_types
            ]
            self._result = rows

        elif "GROUP BY DATE" in q:
            # _history_series_7d: daily average of already-elapsed
            # forecast-v2 rows over the last 7 days. No latest-batch
            # disambiguation needed — the real unique key guarantees at
            # most one row per (venue, hour) ever existed.
            venue_ids = params
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            by_day = {}
            for vid in venue_ids:
                entries = self._store.get("busyness_forecasts", {}).get(vid, [])
                entries = [f for f in entries if f.get("model_version", "forecast-v2") == "forecast-v2"]
                for f in entries:
                    ff = f["forecast_for"]
                    if seven_days_ago <= ff < now:
                        by_day.setdefault(ff.date(), []).append(f["predicted_score"])
            rows = [(day, sum(scores) / len(scores)) for day, scores in sorted(by_day.items())]
            self._result = rows

        elif "bf.venue_id IN" in q:
            # _nearest_v2_forecast_by_venue: nearest future forecast-v2 row
            # per venue_id, from each venue's latest generation batch.
            venue_ids = params
            now = datetime.now(timezone.utc)
            rows = []
            for vid in venue_ids:
                entries = self._store.get("busyness_forecasts", {}).get(vid, [])
                entries = [f for f in entries if f.get("model_version", "forecast-v2") == "forecast-v2"]
                generated_ats = [f["generated_at"] for f in entries if f.get("generated_at") is not None]
                if generated_ats:
                    latest_generated_at = max(generated_ats)
                    entries = [f for f in entries if f.get("generated_at") == latest_generated_at]
                future = sorted(
                    (f for f in entries if f["forecast_for"] >= now),
                    key=lambda f: f["forecast_for"],
                )
                if future:
                    f = future[0]
                    rows.append((
                        vid,
                        f["forecast_for"],
                        f["predicted_score"],
                        f.get("predicted_level"),
                        f.get("estimated_wait_minutes"),
                    ))
            self._result = rows

        elif "FROM busyness_forecasts bf" in q and "JOIN venues v" in q and "v.district = %s" in q:
            # _best_travel_window / _prediction_series: cross-venue average
            # per forecast_for hour, grouped across every venue in district.
            district = params[0]
            now = datetime.now(timezone.utc)
            by_hour = {}
            for v in self._store.get("venues", []):
                if v.get("district") != district:
                    continue
                forecasts = self._store.get("busyness_forecasts", {}).get(v["venue_id"], [])

                # model_version = 'forecast-v2' — default to v2 for fixtures
                # that don't bother setting it (most existing tests).
                forecasts = [f for f in forecasts if f.get("model_version", "forecast-v2") == "forecast-v2"]

                # generated_at = MAX(generated_at) per venue — only the
                # latest batch counts; older/superseded runs are excluded.
                generated_ats = [f["generated_at"] for f in forecasts if f.get("generated_at") is not None]
                if generated_ats:
                    latest_generated_at = max(generated_ats)
                    forecasts = [f for f in forecasts if f.get("generated_at") == latest_generated_at]

                # forecast_for >= UTC_TIMESTAMP() — never surface a forecast
                # for a time that's already passed.
                forecasts = [f for f in forecasts if f["forecast_for"] >= now]

                for f in forecasts:
                    by_hour.setdefault(f["forecast_for"], []).append(f["predicted_score"])
            rows = [(hour, sum(scores) / len(scores)) for hour, scores in sorted(by_hour.items())]
            if "LIMIT 12" in q:
                rows = rows[:12]
            self._result = rows

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

def _make_store(district="MN05", num_venues=3, venue_type="clinic"):
    """venues[i]'s nearest (h=0 / +1h) forecast score is 25 + i*5; the
    _prediction_series/_best_travel_window cross-venue-average tests below
    depend on the full 25 + h*10 + i*5 series across all three hours."""
    now = datetime.now(timezone.utc)
    venues = []
    forecasts = {}

    for i in range(num_venues):
        vid = f"v_test_{i + 1}"
        venues.append({
            "venue_id": vid,
            "name": f"Test Venue {i + 1}",
            "district": district,
            "venue_type": venue_type,
            "language_tags": json.dumps(["EN", "ES"] if i == 0 else ["EN"]),
            "accessible_status": "full_access" if i == 0 else "partial",
        })
        forecasts[vid] = [
            {
                "forecast_for": now + timedelta(hours=h + 1),
                "predicted_score": 25 + h * 10 + i * 5,
                "predicted_level": "quiet",
                "estimated_wait_minutes": 5 + i * 5,
            }
            for h in range(3)
        ]

    return {
        "venues": venues,
        "busyness_forecasts": forecasts,
    }


# ---------------------------------------------------------------------------
# D3.5: _real_time_density
# ---------------------------------------------------------------------------

def test_density_empty_district_returns_zero():
    store = {"venues": [], "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "NONEXISTENT")
    assert result["percent"] == 0
    assert "no data" in result["trend"]


def test_density_single_venue():
    store = _make_store("MN05", num_venues=1)
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 25  # nearest-row score for venue i=0


def test_density_multi_venue_average():
    store = _make_store("MN05", num_venues=3)
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 30  # avg(25, 30, 35)


def test_density_different_district_not_included():
    store = _make_store("MN05", num_venues=2)
    store["venues"].append({
        "venue_id": "v_bk_1", "name": "BK Venue", "district": "BK02",
        "venue_type": "clinic", "language_tags": "[]", "accessible_status": "none",
    })
    now = datetime.now(timezone.utc)
    store["busyness_forecasts"]["v_bk_1"] = [{
        "forecast_for": now + timedelta(hours=1), "predicted_score": 90,
        "predicted_level": "busy", "estimated_wait_minutes": 20,
    }]
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 28  # round(avg(25, 30)) — BK venue excluded


def test_density_excludes_ineligible_venue_types():
    """An AED with a strong (low-busyness) V2 forecast must never lower the
    district's average — it's not V2-predictable, so it never enters the
    query at all."""
    store = _make_store("MN05", num_venues=1)
    now = datetime.now(timezone.utc)
    store["venues"].append({
        "venue_id": "v_aed", "name": "AED", "district": "MN05",
        "venue_type": "emergencyasset", "language_tags": "[]", "accessible_status": "none",
    })
    store["busyness_forecasts"]["v_aed"] = [{
        "forecast_for": now + timedelta(hours=1), "predicted_score": 1,
        "predicted_level": "quiet", "estimated_wait_minutes": 0,
    }]
    cur = _FakeCursor(store)
    result = insights_module._real_time_density(cur, "MN05")
    assert result["percent"] == 25  # unchanged from the single-clinic case


# ---------------------------------------------------------------------------
# D3.5: _best_travel_window
# ---------------------------------------------------------------------------

def test_travel_window_empty_returns_placeholder():
    store = {"venues": [], "busyness_forecasts": {}}
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
        "busyness_forecasts": {
            "v1": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] == result["end_time"]


def test_travel_window_ignores_stale_model_version():
    """A superseded (non-v2) forecast row must never be selected, even if
    it's the only row available for that hour."""
    now = datetime.now(timezone.utc)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05"}],
        "busyness_forecasts": {
            "v1": [
                {"forecast_for": now + timedelta(hours=1), "predicted_score": 5,
                 "model_version": "forecast-v1", "generated_at": now},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] is None
    assert result["cta_label"] == "Check back soon"


def test_travel_window_ignores_superseded_batch():
    """An older generated_at batch for the same venue/hour must be excluded
    once a newer batch exists — otherwise stale and fresh scores get
    averaged together."""
    now = datetime.now(timezone.utc)
    stale_batch = now - timedelta(days=1)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05"}],
        "busyness_forecasts": {
            "v1": [
                {"forecast_for": now + timedelta(hours=1), "predicted_score": 90,
                 "model_version": "forecast-v2", "generated_at": stale_batch},
                {"forecast_for": now + timedelta(hours=1), "predicted_score": 10,
                 "model_version": "forecast-v2", "generated_at": now},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "MN05")
    assert result == [10]


def test_travel_window_ignores_past_forecast_times():
    """A forecast_for timestamp that has already passed must never be
    surfaced as an upcoming travel window."""
    now = datetime.now(timezone.utc)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05"}],
        "busyness_forecasts": {
            "v1": [
                {"forecast_for": now - timedelta(hours=2), "predicted_score": 15,
                 "model_version": "forecast-v2", "generated_at": now},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._best_travel_window(cur, "MN05")
    assert result["start_time"] is None
    assert result["cta_label"] == "Check back soon"


# ---------------------------------------------------------------------------
# D3.5: _fastest_hubs
# ---------------------------------------------------------------------------

def test_hubs_empty_district():
    store = {"venues": [], "busyness_forecasts": {}}
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
        "busyness_forecasts": {
            "v_low": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 20,
                       "predicted_level": "quiet", "estimated_wait_minutes": 3}],
            "v_mid": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 55,
                       "predicted_level": "moderate", "estimated_wait_minutes": 10}],
            "v_high": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 85,
                        "predicted_level": "busy", "estimated_wait_minutes": 25}],
        },
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
        "busyness_forecasts": {
            "v_scored": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40,
                          "predicted_level": "moderate", "estimated_wait_minutes": 8}],
        },
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


def test_hubs_excludes_aed_and_restroom():
    """AED/restroom must never appear in fastest_hubs, even with a strong
    (low-busyness) V2 forecast on file — historical V2 rows exist for them,
    but the SOP's eligibility rule can't be inferred from that data."""
    now = datetime.now(timezone.utc)
    store = _make_store("MN05", num_venues=1)
    store["venues"].append({
        "venue_id": "v_aed", "name": "AED", "district": "MN05",
        "venue_type": "emergencyasset", "language_tags": "[]", "accessible_status": "none",
    })
    store["busyness_forecasts"]["v_aed"] = [{
        "forecast_for": now + timedelta(hours=1), "predicted_score": 1,
        "predicted_level": "quiet", "estimated_wait_minutes": 0,
    }]
    store["venues"].append({
        "venue_id": "v_wc", "name": "Restroom", "district": "MN05",
        "venue_type": "restroom", "language_tags": "[]", "accessible_status": "none",
    })
    store["busyness_forecasts"]["v_wc"] = [{
        "forecast_for": now + timedelta(hours=1), "predicted_score": 1,
        "predicted_level": "quiet", "estimated_wait_minutes": 0,
    }]

    cur = _FakeCursor(store)
    result = insights_module._fastest_hubs(cur, "MN05")

    venue_ids = [hub["venue_id"] for hub in result]
    assert "v_aed" not in venue_ids
    assert "v_wc" not in venue_ids
    assert venue_ids == ["v_test_1"]


# ---------------------------------------------------------------------------
# D3.5/D3.7: _prediction_series
# ---------------------------------------------------------------------------

def test_prediction_series_empty():
    store = {"venues": [], "busyness_forecasts": {}}
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
# D3.5/D3.7: _history_series_7d
# ---------------------------------------------------------------------------

def test_history_series_7d_empty_district():
    store = {"venues": [], "busyness_forecasts": {}}
    cur = _FakeCursor(store)
    result = insights_module._history_series_7d(cur, "NONEXISTENT")
    assert result == []


def test_history_series_7d_averages_past_rows_by_day():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v1", "name": "V1", "district": "MN05", "venue_type": "clinic"},
            {"venue_id": "v2", "name": "V2", "district": "MN05", "venue_type": "clinic"},
        ],
        "busyness_forecasts": {
            "v1": [
                {"forecast_for": now - timedelta(days=1, hours=1), "predicted_score": 20},
                {"forecast_for": now - timedelta(days=2, hours=1), "predicted_score": 40},
            ],
            "v2": [
                {"forecast_for": now - timedelta(days=1, hours=2), "predicted_score": 30},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._history_series_7d(cur, "MN05")
    # 2 days of data: yesterday averages v1(20) and v2(30) = 25; the day
    # before only has v1's 40. Ordered oldest first.
    assert result == [40, 25]


def test_history_series_7d_excludes_future_and_older_than_7_days():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05", "venue_type": "clinic"}],
        "busyness_forecasts": {
            "v1": [
                # Still in the future — not history yet.
                {"forecast_for": now + timedelta(hours=1), "predicted_score": 99},
                # Older than the 7-day window.
                {"forecast_for": now - timedelta(days=8), "predicted_score": 99},
                # The only row that should survive.
                {"forecast_for": now - timedelta(days=3), "predicted_score": 45},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._history_series_7d(cur, "MN05")
    assert result == [45]


def test_history_series_7d_excludes_ineligible_venue_types():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [
            {"venue_id": "v_clinic", "name": "Clinic", "district": "MN05", "venue_type": "clinic"},
            {"venue_id": "v_aed", "name": "AED", "district": "MN05", "venue_type": "emergencyasset"},
        ],
        "busyness_forecasts": {
            "v_clinic": [{"forecast_for": now - timedelta(days=1), "predicted_score": 40}],
            "v_aed": [{"forecast_for": now - timedelta(days=1), "predicted_score": 1}],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._history_series_7d(cur, "MN05")
    assert result == [40]  # the AED's score never enters the average


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
    assert data["data_mode"] in ("db", "mock", "no_data")


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
        "busyness_forecasts": {
            "v_a": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 50,
                     "predicted_level": "moderate", "estimated_wait_minutes": 10}],
            "v_b": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 50,
                     "predicted_level": "moderate", "estimated_wait_minutes": 10}],
        },
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
        "busyness_forecasts": {
            "v_fast": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 50,
                        "predicted_level": "moderate", "estimated_wait_minutes": 5}],
            "v_slow": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 50,
                        "predicted_level": "moderate", "estimated_wait_minutes": 15}],
        },
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
        "busyness_forecasts": {
            "v1": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
            "v2": [{"forecast_for": now + timedelta(hours=1), "predicted_score": 40}],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "MN05")
    assert result == [40]


def test_prediction_series_excludes_past_and_stale_rows():
    now = datetime.now(timezone.utc)
    store = {
        "venues": [{"venue_id": "v1", "name": "V1", "district": "MN05"}],
        "busyness_forecasts": {
            "v1": [
                # Already passed — must be excluded.
                {"forecast_for": now - timedelta(hours=1), "predicted_score": 99,
                 "model_version": "forecast-v2", "generated_at": now},
                # Superseded model version — must be excluded.
                {"forecast_for": now + timedelta(hours=1), "predicted_score": 99,
                 "model_version": "nyc_traffic_context_v1", "generated_at": now},
                # The only row that should survive.
                {"forecast_for": now + timedelta(hours=2), "predicted_score": 33,
                 "model_version": "forecast-v2", "generated_at": now},
            ],
        },
    }
    cur = _FakeCursor(store)
    result = insights_module._prediction_series(cur, "MN05")
    assert result == [33]

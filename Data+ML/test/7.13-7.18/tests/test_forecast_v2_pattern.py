from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

import forecast_v2_pattern as pattern
from forecast_v2_pattern import (
    ELIGIBLE_VENUE_TYPES,
    ENRICHED_FEATURES,
    FORECAST_HORIZON_HOURS,
    eligible_venues,
    feature_matrix,
    forecast_timestamp_for_storage,
    future_curve,
    group_split,
    manhattan_forecast_hour,
    serving_base,
    temporal_snapshot_split,
)

NOW = pd.Timestamp("2026-07-24 12:00:00", tz="UTC")


def test_manhattan_forecast_hour_uses_local_business_time():
    now = manhattan_forecast_hour(datetime(2026, 7, 24, 12, 34, tzinfo=timezone.utc))

    assert str(now) == "2026-07-24 08:00:00-04:00"


def test_forecast_timestamp_for_storage_converts_manhattan_time_to_utc():
    stored = forecast_timestamp_for_storage(pd.Timestamp("2026-07-24 08:00:00", tz="America/New_York"))

    assert stored == datetime(2026, 7, 24, 12, 0)


def _valid_curve(now: pd.Timestamp = NOW, venue_type: str = "clinic") -> pd.DataFrame:
    """13-point hourly curve starting at now, single eligible venue."""
    rows = []
    for i in range(FORECAST_HORIZON_HOURS + 1):
        rows.append({
            "venue_id": "v1",
            "venue_type": venue_type,
            "forecast_for": now + pd.Timedelta(hours=i),
        })
    return pd.DataFrame(rows)


def test_group_split_keeps_place_ids_disjoint():
    rows = []
    for place in range(10):
        for hour in range(3):
            rows.append({"place_id": f"p{place}", "venue_id": f"v{place}", "label_score": hour})
    train, val, test = group_split(pd.DataFrame(rows))
    assert not (set(train.place_id) & set(val.place_id))
    assert not (set(train.place_id) & set(test.place_id))
    assert not (set(val.place_id) & set(test.place_id))


def test_temporal_snapshot_split_uses_only_earlier_snapshot_for_training():
    old = pd.DataFrame([
        {"venue_id": "v1", "place_id": "p1", "day_of_week": 0, "hour_of_day": 9, "busyness_score": 10},
        {"venue_id": "v2", "place_id": "p2", "day_of_week": 0, "hour_of_day": 9, "busyness_score": 20},
    ])
    current = old.assign(busyness_score=[30, 40])
    train, test = temporal_snapshot_split(old, current)
    assert train.busyness_score.tolist() == [10, 20]
    assert test.busyness_score.tolist() == [30, 40]
    assert set(test.venue_id).issubset(set(train.venue_id))


def test_feature_matrix_keeps_enriched_columns_stable():
    features = ["venue_id", "rating"]
    train = pd.DataFrame({"venue_id": ["v1", "v2"], "rating": [4.0, None]})
    test = pd.DataFrame({"venue_id": ["v1"], "rating": [None]})
    columns = feature_matrix(train, features).columns.tolist()
    assert feature_matrix(test, features, columns).columns.tolist() == columns


def test_traffic_features_are_part_of_the_enriched_supervised_input():
    assert "nyc_traffic_baseline_score" in ENRICHED_FEATURES
    assert "nyc_traffic_baseline_missing" in ENRICHED_FEATURES


def test_traffic_feature_missingness_is_explicit_and_matrix_is_stable():
    features = ["nyc_traffic_baseline_score", "nyc_traffic_baseline_missing"]
    train = pd.DataFrame({"nyc_traffic_baseline_score": [55, 0], "nyc_traffic_baseline_missing": [0, 1]})
    test = pd.DataFrame({"nyc_traffic_baseline_score": [0], "nyc_traffic_baseline_missing": [1]})
    columns = feature_matrix(train, features).columns.tolist()
    assert feature_matrix(test, features, columns).columns.tolist() == columns


def test_serving_curve_includes_unlabelled_eligible_venues_and_excludes_ineligible():
    eligible = pd.DataFrame([
        {"venue_id": "labelled", "venue_type": "clinic", "district": "d", "rating": 4.0,
         "latitude": 40.7, "longitude": -74.0, "weather_risk": None, "source_confidence": 1.0,
         "accessible_status": None, "active_warning": 0, "open_now": 1},
        {"venue_id": "cold_start", "venue_type": "pharmacy", "district": "d", "rating": None,
         "latitude": 40.8, "longitude": -73.9, "weather_risk": None, "source_confidence": 1.0,
         "accessible_status": None, "active_warning": 0, "open_now": 1},
    ])
    curve = future_curve(serving_base(eligible), NOW)
    assert set(curve.venue_id) == {"labelled", "cold_start"}
    assert len(curve) == 2 * (FORECAST_HORIZON_HOURS + 1)
    assert curve.loc[curve.venue_id == "cold_start", "rating_missing"].eq(1).all()


def test_all_medical_venue_types_are_eligible_for_cold_start_serving():
    assert ELIGIBLE_VENUE_TYPES == {
        "healthcare", "clinic", "hospital", "pharmacy", "dentist", "laboratory",
    }

    eligible = pd.DataFrame([
        {"venue_id": f"v_{venue_type}", "venue_type": venue_type, "district": "d", "rating": None,
         "latitude": 40.7, "longitude": -74.0, "weather_risk": None, "source_confidence": 1.0,
         "accessible_status": None, "active_warning": 0, "open_now": 1}
        for venue_type in ELIGIBLE_VENUE_TYPES
    ])
    curve = future_curve(serving_base(eligible), NOW)
    assert set(curve.venue_type) == ELIGIBLE_VENUE_TYPES
    assert len(curve) == len(ELIGIBLE_VENUE_TYPES) * (FORECAST_HORIZON_HOURS + 1)


def test_eligible_venues_query_is_limited_to_v2_approved_types(monkeypatch):
    captured = {}

    def read_sql(query, params=()):
        captured["query"], captured["params"] = query, params
        return pd.DataFrame()

    monkeypatch.setattr(pattern.db_utils, "read_sql", read_sql)
    eligible_venues()
    assert "venue_type IN" in captured["query"]
    assert set(captured["params"]) == ELIGIBLE_VENUE_TYPES


def test_publish_upserts_backend_forecast_contract(monkeypatch):
    cursor, conn = MagicMock(), MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(pattern.db_utils, "get_conn", lambda: conn)
    curve = pd.DataFrame({
        "venue_id": ["v1"], "forecast_for": [pd.Timestamp(datetime(2026, 7, 18, 12), tz="UTC")],
        "predicted_score": [61.4], "predicted_level": ["moderate"],
    })
    assert pattern.publish_forecasts(curve) == 1
    sql, rows = cursor.executemany.call_args.args
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert rows[0][5] == "forecast-v2"
    conn.commit.assert_called_once()


def test_audit_curve_passes_valid_13_point_curve():
    curve = _valid_curve(NOW)
    audit = pattern.audit_curve(curve, NOW)
    assert audit["type_counts"] == {"clinic": 1}
    assert audit["future_rows"] == 13
    assert NOW.strftime("%Y-%m-%d %H") in audit["min_forecast_for"]


def test_audit_curve_fails_on_empty_curve():
    with pytest.raises(ValueError, match="Curve is empty"):
        pattern.audit_curve(pd.DataFrame(), NOW)


def test_audit_curve_fails_on_stale_curve():
    stale_now = NOW - pd.Timedelta(hours=24)
    curve = _valid_curve(stale_now)
    with pytest.raises(ValueError, match="Zero future rows"):
        pattern.audit_curve(curve, NOW)


def test_audit_curve_fails_on_ineligible_venue_type():
    curve = _valid_curve(NOW, venue_type="restroom")
    with pytest.raises(ValueError, match="Ineligible venue types.*restroom"):
        pattern.audit_curve(curve, NOW)


def test_audit_curve_fails_when_max_forecast_too_short():
    # Only 10 points instead of 13
    rows = []
    for i in range(10):
        rows.append({
            "venue_id": "v1",
            "venue_type": "hospital",
            "forecast_for": NOW + pd.Timedelta(hours=i),
        })
    curve = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="does not reach required"):
        pattern.audit_curve(curve, NOW)


def test_audit_curve_fails_when_venue_missing_hour_buckets():
    # Skip hour 5
    rows = []
    for i in range(FORECAST_HORIZON_HOURS + 1):
        if i == 5:
            continue
        rows.append({
            "venue_id": "v1",
            "venue_type": "pharmacy",
            "forecast_for": NOW + pd.Timedelta(hours=i),
        })
    curve = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="missing forecast slots"):
        pattern.audit_curve(curve, NOW)


def test_audit_curve_fails_when_one_venue_is_fully_stale():
    """A batch with one fresh venue and one fully-stale venue must not pass."""
    fresh_rows = [
        {"venue_id": "fresh", "venue_type": "clinic",
         "forecast_for": NOW + pd.Timedelta(hours=i)}
        for i in range(FORECAST_HORIZON_HOURS + 1)
    ]
    stale_rows = [
        {"venue_id": "stale", "venue_type": "clinic",
         "forecast_for": NOW - pd.Timedelta(days=5) + pd.Timedelta(hours=i)}
        for i in range(FORECAST_HORIZON_HOURS + 1)
    ]
    curve = pd.DataFrame(fresh_rows + stale_rows)
    with pytest.raises(ValueError, match="missing forecast slots"):
        pattern.audit_curve(curve, NOW)


def test_audit_curve_fails_when_an_eligible_serving_venue_is_missing():
    curve = _valid_curve()
    with pytest.raises(ValueError, match="Serving venue coverage mismatch.*missing.*v2"):
        pattern.audit_curve(curve, NOW, {"v1", "v2"})


def test_audit_curve_fails_on_duplicate_future_slot():
    curve = pd.concat([_valid_curve(), _valid_curve().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="missing forecast slots"):
        pattern.audit_curve(curve, NOW)

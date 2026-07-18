from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd

import forecast_v2_pattern as pattern
from forecast_v2_pattern import ENRICHED_FEATURES, feature_matrix, group_split, temporal_snapshot_split


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

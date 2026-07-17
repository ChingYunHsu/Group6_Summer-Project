import pandas as pd

from forecast_v2_pattern import feature_matrix, group_split, temporal_snapshot_split


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

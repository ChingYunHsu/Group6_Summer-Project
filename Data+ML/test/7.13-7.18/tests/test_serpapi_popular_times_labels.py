from pathlib import Path

import pandas as pd

from serpapi_popular_times_labels import build_labels, parse_hour


def test_parse_hour_handles_midnight_and_noon():
    assert parse_hour("12 AM") == 0
    assert parse_hour("12 PM") == 12
    assert parse_hour("6 PM") == 18


def test_build_labels_excludes_missing_graph_rows(tmp_path: Path):
    source = tmp_path / "snapshot.csv"
    pd.DataFrame([
        {"snapshot_id": "s1", "captured_at": "2026-07-16T00:00:00Z", "venue_id": "v1", "place_id": "p1", "day": "monday", "hour": "6 AM", "busyness_score": 0, "has_popular_times": True},
        {"snapshot_id": "s1", "captured_at": "2026-07-16T00:00:00Z", "venue_id": "v2", "place_id": "p2", "day": "", "hour": "", "busyness_score": "", "has_popular_times": False},
    ]).to_csv(source, index=False)
    labels, manifest = build_labels(source)
    assert len(labels) == 1
    assert labels.iloc[0]["busyness_score"] == 0
    assert labels.iloc[0]["target_type"] == "google_popular_times_proxy"
    assert manifest["venues"] == 1

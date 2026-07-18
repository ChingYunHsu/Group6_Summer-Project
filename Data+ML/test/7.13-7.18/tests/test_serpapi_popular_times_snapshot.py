from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import serpapi_popular_times_snapshot as snapshots


def test_snapshot_rows_extracts_hourly_scores_and_live_status():
    rows = snapshots.snapshot_rows(
        snapshots.PlaceTarget(place_id="place-1", venue_id="venue-1"),
        {"place_results": {"title": "Clinic", "popular_times": {
            "live_hash": {"info": "Less busy than usual"},
            "graph_results": {"monday": [{"time": "9 AM", "busyness_score": 42}]},
        }}},
        "baseline", "2026-07-16T00:00:00+00:00",
    )
    assert rows == [{
        "snapshot_id": "baseline", "captured_at": "2026-07-16T00:00:00+00:00",
        "venue_id": "venue-1", "place_id": "place-1", "title": "Clinic",
        "live_info": "Less busy than usual", "has_popular_times": True,
        "day": "monday", "hour": "9 AM", "busyness_score": 42.0,
    }]


def test_run_snapshot_and_compare_writes_repeatable_artifacts(tmp_path):
    targets = [snapshots.PlaceTarget(place_id="place-1", venue_id="venue-1")]

    def baseline_fetcher(place_id, _key):
        return {"place_results": {"popular_times": {"live_hash": {"info": "Busy"}, "graph_results": {"monday": [{"time": "9 AM", "busyness_score": 40}]}}}}

    baseline_path, metadata = snapshots.run_snapshot(targets, tmp_path, "baseline", "fake", baseline_fetcher, 0)
    assert metadata["popular_times_target_count"] == 1

    def later_fetcher(place_id, _key):
        return {"place_results": {"popular_times": {"live_hash": {"info": "Less busy than usual"}, "graph_results": {"monday": [{"time": "9 AM", "busyness_score": 55}]}}}}

    later_path, _ = snapshots.run_snapshot(targets, tmp_path, "later", "fake", later_fetcher, 0)
    comparison, summary = snapshots.compare_snapshots(snapshots.read_csv(baseline_path), snapshots.read_csv(later_path))
    assert comparison[0]["score_change"] == 15.0
    assert comparison[0]["live_info_changed"] is True
    assert summary["mean_absolute_score_change"] == 15.0
    assert (tmp_path / "baseline" / "raw").glob("*.json")


def test_load_targets_requires_place_id_and_deduplicates(tmp_path):
    path = tmp_path / "places.csv"
    path.write_text("place_id,venue_id\na,v1\na,v1\nb,v2\n", encoding="utf-8")
    assert snapshots.load_targets(path) == [snapshots.PlaceTarget("a", "v1"), snapshots.PlaceTarget("b", "v2")]


def test_targets_from_label_view_picks_stable_priority_cohort(tmp_path):
    path = tmp_path / "labels.csv"
    path.write_text(
        "venue_id,serpapi_place_id,ml_eligible,priority_score\n"
        "v2,p2,True,1\n"
        "v1,p1,True,9\n"
        "v3,p1,True,99\n"
        "v4,p4,False,100\n",
        encoding="utf-8",
    )
    assert snapshots.targets_from_label_view(path, 2) == [
        snapshots.PlaceTarget("p1", "v3"), snapshots.PlaceTarget("p1", "v1"),
    ]


def test_run_snapshot_reuses_one_api_response_for_shared_place(tmp_path):
    calls = []
    targets = [snapshots.PlaceTarget("p1", "v1"), snapshots.PlaceTarget("p1", "v2")]

    def fetcher(place_id, _key):
        calls.append(place_id)
        return {"place_results": {"popular_times": {"graph_results": {"monday": [{"time": "9 AM", "busyness_score": 40}]}}}}

    path, metadata = snapshots.run_snapshot(targets, tmp_path, "shared", "fake", fetcher, 0)
    rows = snapshots.read_csv(path)
    assert calls == ["p1"]
    assert {row["venue_id"] for row in rows} == {"v1", "v2"}
    assert metadata["api_call_count"] == 1


def test_run_snapshot_stops_on_quota_error_and_reports_progress(tmp_path):
    messages = []

    def quota_fetcher(_place_id, _key):
        raise snapshots.SerpAPIRequestError(429, "quota exceeded")

    path, metadata = snapshots.run_snapshot(
        [snapshots.PlaceTarget("p1", "v1"), snapshots.PlaceTarget("p2", "v2")],
        tmp_path, "quota", "fake", quota_fetcher, 0, messages.append,
    )
    assert path.exists()
    assert metadata["failure_count"] == 1
    assert "HTTP 429" in metadata["halted_reason"]
    assert any("1/2" in message for message in messages)


def test_baseline_rows_reads_only_matching_place_api_json(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "place.json").write_text(
        '{"search_parameters":{"place_id":"p1"},"search_metadata":{"created_at":"old"},'
        '"place_results":{"popular_times":{"graph_results":{"monday":[{"time":"9 AM","busyness_score":44}]}}}}',
        encoding="utf-8",
    )
    (raw / "search.json").write_text('{"search_parameters":{"q":"clinic"},"local_results":[]}', encoding="utf-8")
    rows = snapshots.baseline_rows_from_raw_json(raw, [snapshots.PlaceTarget("p1", "v1")])
    assert len(rows) == 1
    assert rows[0]["busyness_score"] == 44.0

"""Export a versioned weak-label dataset from a SerpAPI Popular Times snapshot.

Google Popular Times is the V2 target proxy, never a model input feature.
This module only transforms an already captured snapshot; it makes no API calls
and does not write to the database.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from score_utils import score_to_level


DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6}


def parse_hour(label: Any) -> int | None:
    match = re.fullmatch(r"\s*(\d{1,2})\s*([AP]M)\s*", str(label).upper())
    if not match:
        return None
    hour = int(match.group(1))
    if not 1 <= hour <= 12:
        return None
    return (hour % 12) + (12 if match.group(2) == "PM" else 0)


def build_labels(snapshot_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    snapshot = pd.read_csv(snapshot_path, dtype={"venue_id": str, "place_id": str})
    required = {"snapshot_id", "captured_at", "venue_id", "place_id", "day", "hour", "busyness_score", "has_popular_times"}
    missing = required - set(snapshot.columns)
    if missing:
        raise ValueError(f"Snapshot missing required columns: {sorted(missing)}")
    labels = snapshot[snapshot["has_popular_times"].astype(str).str.lower().eq("true")].copy()
    labels["day_name"] = labels["day"].astype(str).str.lower()
    labels["hour_of_day"] = labels["hour"].map(parse_hour)
    labels["busyness_score"] = pd.to_numeric(labels["busyness_score"], errors="coerce")
    labels = labels[labels["day_name"].isin(DAYS) & labels["hour_of_day"].notna() & labels["busyness_score"].notna()].copy()
    labels["day_of_week"] = labels["day_name"].map(DAYS)
    labels["busyness_score"] = labels["busyness_score"].astype(int)
    labels["label_level"] = labels["busyness_score"].map(score_to_level)
    labels["target_type"] = "google_popular_times_proxy"
    labels["label_provenance"] = "serpapi_google_maps_place_snapshot"
    columns = ["snapshot_id", "captured_at", "venue_id", "place_id", "day_name", "day_of_week", "hour_of_day", "busyness_score", "label_level", "target_type", "label_provenance"]
    labels = labels[columns].sort_values(["venue_id", "day_of_week", "hour_of_day"]).reset_index(drop=True)
    manifest = {
        "target_type": "google_popular_times_proxy",
        "label_provenance": "serpapi_google_maps_place_snapshot",
        "source_snapshot": str(snapshot_path),
        "snapshot_ids": sorted(labels["snapshot_id"].unique().tolist()),
        "label_rows": len(labels),
        "venues": labels["venue_id"].nunique(),
        "places": labels["place_id"].nunique(),
        "score_min": int(labels["busyness_score"].min()) if not labels.empty else None,
        "score_max": int(labels["busyness_score"].max()) if not labels.empty else None,
    }
    return labels, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SerpAPI Popular Times weak-label CSV")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    labels, manifest = build_labels(args.snapshot)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    labels.to_csv(args.output_dir / "serpapi_popular_times_weak_labels.csv", index=False)
    (args.output_dir / "label_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

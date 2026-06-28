"""Run DB-driven SerpAPI checks for uncovered healthcare venues.

This task is intentionally isolated from the existing discovery result:
- input is venue_label_status.csv
- only healthcare rows with label_status == api_not_checked are eligible
- previously covered healthcare rows are never queried
- previous rows in healthcare_uncovered_batch_results.csv are skipped

Default mode is dry-run. Use --confirm-live-api to spend SerpAPI quota.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from venue_serpapi import EARTH_RADIUS_M, _serpapi_request


DEFAULT_LABEL_FILE = Path("../output/venue_label_status.csv")
DEFAULT_OUTPUT_FILE = Path("../output/healthcare_uncovered_batch_results.csv")


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return haversine distance in meters."""
    lat1_rad = np.radians(lat1)
    lng1_rad = np.radians(lng1)
    lat2_rad = np.radians(lat2)
    lng2_rad = np.radians(lng2)
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlng / 2) ** 2
    )
    return float(EARTH_RADIUS_M * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def load_uncovered_healthcare(label_file: Path) -> pd.DataFrame:
    """Load healthcare venues that have not been covered by the prior run."""
    labels = pd.read_csv(label_file)
    required = {"venue_id", "venue_type", "label_status", "name", "latitude", "longitude"}
    missing = required - set(labels.columns)
    if missing:
        raise ValueError(f"Missing required columns in {label_file}: {sorted(missing)}")

    uncovered = labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"] == "api_not_checked")
    ].copy()
    return uncovered.sort_values(["district", "venue_id"]).reset_index(drop=True)


def load_done_venue_ids(output_file: Path) -> set[str]:
    """Return venue_ids already written by previous uncovered batch runs."""
    if not output_file.exists():
        return set()
    previous = pd.read_csv(output_file, usecols=["venue_id"])
    return set(previous["venue_id"].dropna().astype(str))


def choose_batch(
    uncovered: pd.DataFrame,
    output_file: Path,
    batch_size: int,
    batch_index: int,
    skip_existing: bool,
) -> pd.DataFrame:
    """Select one batch from uncovered venues, optionally skipping prior outputs."""
    candidates = uncovered
    if skip_existing:
        done_ids = load_done_venue_ids(output_file)
        candidates = candidates[~candidates["venue_id"].astype(str).isin(done_ids)]

    start = batch_index * batch_size
    end = start + batch_size
    return candidates.iloc[start:end].copy().reset_index(drop=True)


def parse_search_result(
    venue: pd.Series,
    result: dict[str, Any],
    rank: int,
    match_radius_m: float,
) -> dict[str, Any] | None:
    """Return normalized result if it has coordinates within the match radius."""
    gps = result.get("gps_coordinates") or {}
    lat = gps.get("latitude")
    lng = gps.get("longitude")
    if lat is None or lng is None:
        return None

    distance_m = haversine_distance_m(
        float(venue["latitude"]),
        float(venue["longitude"]),
        float(lat),
        float(lng),
    )
    if distance_m > match_radius_m:
        return None

    return {
        "search_result_rank": rank,
        "match_distance_m": round(distance_m, 3),
        "serpapi_place_id": result.get("place_id"),
        "serpapi_data_id": result.get("data_id"),
        "serpapi_name": result.get("title"),
        "serpapi_type": result.get("type"),
        "reviews": result.get("reviews"),
        "rating": result.get("rating"),
    }


def find_best_serpapi_match(
    venue: pd.Series,
    api_key: str,
    output_dir: Path,
    top_k_results: int,
    match_radius_m: float,
) -> tuple[dict[str, Any] | None, int]:
    """Search one DB venue and return the nearest acceptable SerpAPI match."""
    params = {
        "q": str(venue["name"]),
        "ll": f"@{float(venue['latitude'])},{float(venue['longitude'])},18z",
        "type": "search",
        "hl": "en",
        "gl": "us",
    }
    data = _serpapi_request(
        params,
        api_key,
        output_dir,
        cache_prefix="healthcare_uncovered_search",
    )
    if not data:
        return None, 1

    matches: list[dict[str, Any]] = []
    for rank, result in enumerate(data.get("local_results", [])[:top_k_results], start=1):
        parsed = parse_search_result(venue, result, rank, match_radius_m)
        if parsed:
            matches.append(parsed)

    if not matches:
        return None, 1
    return min(matches, key=lambda item: item["match_distance_m"]), 1


def check_place_popular_times(
    place_id: str | None,
    api_key: str,
    output_dir: Path,
) -> tuple[bool, int]:
    """Check Place API for popular_times."""
    if not place_id:
        return False, 0
    params = {
        "place_id": place_id,
        "type": "place",
        "hl": "en",
    }
    data = _serpapi_request(
        params,
        api_key,
        output_dir,
        cache_prefix="healthcare_uncovered_place",
    )
    if not data or "place_results" not in data:
        return False, 1
    return data["place_results"].get("popular_times") is not None, 1


def build_base_row(
    venue: pd.Series,
    batch_index: int,
    batch_position: int,
    run_id: str,
) -> dict[str, Any]:
    """Build common output columns for one venue."""
    return {
        "run_id": run_id,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "batch_index": batch_index,
        "batch_position": batch_position,
        "venue_id": venue["venue_id"],
        "venue_name": venue["name"],
        "district": venue.get("district"),
        "latitude": venue["latitude"],
        "longitude": venue["longitude"],
        "search_query": venue["name"],
    }


def run_batch(
    label_file: Path,
    output_file: Path,
    batch_size: int,
    batch_index: int,
    top_k_results: int,
    match_radius_m: float,
    place_check: bool,
    dry_run: bool,
    confirm_live_api: bool,
    skip_existing: bool,
    sleep_s: float,
) -> pd.DataFrame:
    """Run one uncovered healthcare batch and append results to CSV."""
    uncovered = load_uncovered_healthcare(label_file)
    batch = choose_batch(uncovered, output_file, batch_size, batch_index, skip_existing)

    print(f"Healthcare uncovered input: {len(uncovered)}")
    print(f"Batch index: {batch_index}")
    print(f"Batch size selected: {len(batch)}")
    print(f"Skip existing output rows: {skip_existing}")
    print(f"Output file: {output_file}")

    if len(batch) == 0:
        return pd.DataFrame()

    if dry_run:
        preview_cols = ["venue_id", "district", "name", "latitude", "longitude"]
        print("Dry-run only. No SerpAPI calls will be made.")
        print(batch[preview_cols].to_string(index=False))
        return batch

    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required for live API runs.")

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows: list[dict[str, Any]] = []
    search_calls = 0
    place_calls = 0

    for position, (_, venue) in enumerate(batch.iterrows(), start=1):
        row = build_base_row(venue, batch_index, position, run_id)
        print(f"[{position}/{len(batch)}] Search: {venue['name']}")

        match, used_search = find_best_serpapi_match(
            venue,
            api_key,
            output_dir,
            top_k_results,
            match_radius_m,
        )
        search_calls += used_search

        if not match:
            row.update({
                "matched": False,
                "place_checked": False,
                "has_popular_times": False,
                "label_status": "api_not_checked",
                "exclude_reason": "no_search_result_within_radius",
            })
            rows.append(row)
            time.sleep(sleep_s)
            continue

        row.update(match)
        row["matched"] = True
        row["exclude_reason"] = ""

        if place_check:
            has_popular_times, used_place = check_place_popular_times(
                match.get("serpapi_place_id"),
                api_key,
                output_dir,
            )
            place_calls += used_place
            row["place_checked"] = True
            row["has_popular_times"] = has_popular_times
            row["label_status"] = "has_popular_times" if has_popular_times else "no_popular_times"
        else:
            row["place_checked"] = False
            row["has_popular_times"] = False
            row["label_status"] = "search_matched_unvalidated"

        rows.append(row)
        time.sleep(sleep_s)

    result = pd.DataFrame(rows)
    append = output_file.exists()
    result.to_csv(output_file, mode="a" if append else "w", header=not append, index=False)

    print("\nBatch complete")
    print(f"Search calls attempted: {search_calls}")
    print(f"Place calls attempted: {place_calls}")
    print(f"Matched venues: {int(result['matched'].sum())}")
    print(f"Has popular_times: {int(result['has_popular_times'].sum())}")
    print(f"Rows appended: {len(result)}")
    return result


def resolve_path(path: str | Path) -> Path:
    """Resolve CLI paths relative to this script directory."""
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-check healthcare venues not covered by prior SerpAPI discovery."
    )
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--batch-index", type=int, default=0)
    parser.add_argument("--top-k-results", type=int, default=3)
    parser.add_argument("--match-radius-m", type=float, default=100)
    parser.add_argument("--sleep-s", type=float, default=1.0)
    parser.add_argument("--no-place-check", action="store_true")
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--confirm-live-api", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--live", action="store_true", help="Disable dry-run; requires --confirm-live-api.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dry_run = not args.live

    run_batch(
        label_file=resolve_path(args.label_file),
        output_file=resolve_path(args.output_file),
        batch_size=args.batch_size,
        batch_index=args.batch_index,
        top_k_results=args.top_k_results,
        match_radius_m=args.match_radius_m,
        place_check=not args.no_place_check,
        dry_run=dry_run,
        confirm_live_api=args.confirm_live_api,
        skip_existing=not args.no_skip_existing,
        sleep_s=args.sleep_s,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

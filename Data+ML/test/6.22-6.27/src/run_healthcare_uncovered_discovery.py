"""Discovery-first coverage check for uncovered healthcare venues.

This is the low-cost first round:
- input pool: healthcare rows still marked api_not_checked
- query pattern: healthcare category x district x paginated Search
- output: local DB venues matched to Google Maps Search results
- no Place API calls here; busy/popular_times validation is a second round

Default mode is dry-run. Use --live --confirm-live-api to spend SerpAPI quota.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from venue_serpapi import (
    DISTRICT_CENTERS,
    EARTH_RADIUS_M,
    SERPAPI_SEARCH_CATEGORIES,
    _serpapi_request,
)


DEFAULT_LABEL_FILE = Path("../output/venue_label_status.csv")
DEFAULT_OUTPUT_FILE = Path("../output/healthcare_uncovered_discovery_matches.csv")
DEFAULT_PRIOR_RESULT_FILE = Path("../output/healthcare_uncovered_batch_results.csv")
DISCOVERY_INPUT_STATUSES = {"api_not_checked", "search_not_matched"}
EXPANDED_HEALTHCARE_SEARCH_CATEGORIES = [
    ("clinic", "medical_clinic", "healthcare"),
    ("doctor", "doctor", "healthcare"),
    ("urgent care", "medical_clinic", "healthcare"),
    ("medical center", "medical_clinic", "healthcare"),
    ("health center", "medical_clinic", "healthcare"),
    ("dental clinic", "dentist", "healthcare"),
    ("drugstore", "pharmacy", "healthcare"),
]


@dataclass
class SearchPlanItem:
    category_query: str
    google_type: str
    clearpath_type: str
    district: str
    start: int


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("&", " and ").split())


def name_similarity(left: Any, right: Any) -> float:
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    return round(SequenceMatcher(None, left_norm, right_norm).ratio(), 4)


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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
    labels = pd.read_csv(label_file)
    uncovered = labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"].isin(DISCOVERY_INPUT_STATUSES))
    ].copy()
    return uncovered.reset_index(drop=True)


def load_existing_venue_ids(paths: list[Path]) -> set[str]:
    existing: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        previous = pd.read_csv(path, usecols=["venue_id"])
        existing.update(previous["venue_id"].dropna().astype(str))
    return existing


def build_search_plan(max_search_calls: int, results_per_page: int) -> list[SearchPlanItem]:
    """Build category/district/page discovery calls, capped by max_search_calls."""
    search_categories = SERPAPI_SEARCH_CATEGORIES + EXPANDED_HEALTHCARE_SEARCH_CATEGORIES
    plan: list[SearchPlanItem] = []
    page = 0
    while len(plan) < max_search_calls:
        start = page * results_per_page
        for category_query, google_type, clearpath_type in search_categories:
            for district in DISTRICT_CENTERS:
                plan.append(SearchPlanItem(
                    category_query=category_query,
                    google_type=google_type,
                    clearpath_type=clearpath_type,
                    district=district,
                    start=start,
                ))
                if len(plan) >= max_search_calls:
                    return plan
        page += 1
    return plan


def find_db_matches(
    venues: pd.DataFrame,
    google_result: dict[str, Any],
    match_radius_m: float,
    min_name_similarity: float,
) -> list[dict[str, Any]]:
    gps = google_result.get("gps_coordinates") or {}
    result_lat = gps.get("latitude")
    result_lng = gps.get("longitude")
    if result_lat is None or result_lng is None:
        return []

    rows: list[dict[str, Any]] = []
    for _, venue in venues.iterrows():
        distance_m = haversine_distance_m(
            float(venue["latitude"]),
            float(venue["longitude"]),
            float(result_lat),
            float(result_lng),
        )
        if distance_m > match_radius_m:
            continue

        similarity = name_similarity(venue["name"], google_result.get("title"))
        if similarity < min_name_similarity:
            continue

        rows.append({
            "venue_id": venue["venue_id"],
            "venue_name": venue["name"],
            "district": venue.get("district"),
            "latitude": venue["latitude"],
            "longitude": venue["longitude"],
            "serpapi_place_id": google_result.get("place_id"),
            "serpapi_data_id": google_result.get("data_id"),
            "serpapi_name": google_result.get("title"),
            "serpapi_type": google_result.get("type"),
            "reviews": google_result.get("reviews"),
            "rating": google_result.get("rating"),
            "distance_m": round(distance_m, 3),
            "name_similarity": similarity,
        })
    return rows


def keep_best_match(existing: dict[str, dict[str, Any]], row: dict[str, Any]) -> None:
    """Keep one best Google match per DB venue."""
    venue_id = str(row["venue_id"])
    current = existing.get(venue_id)
    if current is None:
        existing[venue_id] = row
        return

    current_key = (current["distance_m"], -current["name_similarity"])
    new_key = (row["distance_m"], -row["name_similarity"])
    if new_key < current_key:
        existing[venue_id] = row


def run_discovery(
    label_file: Path,
    output_file: Path,
    prior_result_file: Path,
    max_search_calls: int,
    results_per_page: int,
    match_radius_m: float,
    min_name_similarity: float,
    dry_run: bool,
    confirm_live_api: bool,
    skip_existing: bool,
    sleep_s: float,
) -> pd.DataFrame:
    uncovered = load_uncovered_healthcare(label_file)
    if skip_existing:
        existing_ids = load_existing_venue_ids([output_file, prior_result_file])
        uncovered = uncovered[~uncovered["venue_id"].astype(str).isin(existing_ids)]

    plan = build_search_plan(max_search_calls, results_per_page)
    theoretical_results = len(plan) * results_per_page

    print(f"Healthcare uncovered input: {len(uncovered)}")
    print(f"Discovery Search calls planned: {len(plan)}")
    print(f"Theoretical Google results: {theoretical_results}")
    print(f"Match radius: {match_radius_m}m")
    print(f"Minimum name similarity: {min_name_similarity}")
    print(f"Place API calls planned: 0")
    print(f"Output file: {output_file}")
    print(f"Prior result file skipped: {prior_result_file if prior_result_file.exists() else 'none'}")

    if dry_run:
        print("Dry-run only. No SerpAPI calls will be made.")
        print(pd.DataFrame([item.__dict__ for item in plan]).head(20).to_string(index=False))
        return pd.DataFrame([item.__dict__ for item in plan])

    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required for live API runs.")

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    best_by_venue: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(plan, start=1):
        center = DISTRICT_CENTERS[item.district]
        params = {
            "q": f"{item.category_query} near {item.district.replace('_', ' ')} Manhattan",
            "ll": f"@{center['lat']},{center['lng']},14z",
            "type": "search",
            "hl": "en",
            "gl": "us",
        }
        if item.start:
            params["start"] = item.start

        print(
            f"[{index}/{len(plan)}] Search: {item.category_query} "
            f"{item.district} start={item.start}"
        )
        data = _serpapi_request(params, api_key, output_dir, cache_prefix="search")
        if not data:
            time.sleep(sleep_s)
            continue

        local_results = data.get("local_results", [])[:results_per_page]
        for rank, google_result in enumerate(local_results, start=1):
            for row in find_db_matches(
                uncovered,
                google_result,
                match_radius_m,
                min_name_similarity,
            ):
                row.update({
                    "run_id": run_id,
                    "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "search_category": item.category_query,
                    "search_district": item.district,
                    "search_page_start": item.start,
                    "search_result_rank": rank,
                    "matched": True,
                    "place_checked": False,
                    "has_popular_times": False,
                    "label_status": "search_matched_unvalidated",
                })
                keep_best_match(best_by_venue, row)
        time.sleep(sleep_s)

    result = pd.DataFrame(best_by_venue.values())
    if len(result) > 0:
        result = result.sort_values(["district", "venue_id"]).reset_index(drop=True)
        append = output_file.exists()
        result.to_csv(output_file, mode="a" if append else "w", header=not append, index=False)

    print("\nDiscovery complete")
    print(f"Search calls attempted: {len(plan)}")
    print(f"Matched uncovered venues: {len(result)}")
    print(f"Place calls attempted: 0")
    print(f"Rows appended: {len(result)}")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Low-cost discovery coverage for uncovered healthcare venues."
    )
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--prior-result-file", default=str(DEFAULT_PRIOR_RESULT_FILE))
    parser.add_argument("--max-search-calls", type=int, default=38)
    parser.add_argument("--results-per-page", type=int, default=20)
    parser.add_argument("--match-radius-m", type=float, default=200)
    parser.add_argument("--min-name-similarity", type=float, default=0.4)
    parser.add_argument("--sleep-s", type=float, default=1.0)
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--confirm-live-api", action="store_true")
    parser.add_argument("--live", action="store_true", help="Disable dry-run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    run_discovery(
        label_file=resolve_path(args.label_file),
        output_file=resolve_path(args.output_file),
        prior_result_file=resolve_path(args.prior_result_file),
        max_search_calls=args.max_search_calls,
        results_per_page=args.results_per_page,
        match_radius_m=args.match_radius_m,
        min_name_similarity=args.min_name_similarity,
        dry_run=not args.live,
        confirm_live_api=args.confirm_live_api,
        skip_existing=not args.no_skip_existing,
        sleep_s=args.sleep_s,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

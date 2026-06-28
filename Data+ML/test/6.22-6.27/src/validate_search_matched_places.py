"""Validate search-matched healthcare places with SerpAPI Place API.

This is the second round after discovery:
- input: venue_label_status_coverage_view.csv
- target: healthcare rows with label_status == search_matched_unvalidated
- dedupe: one Place API request per unique serpapi_place_id
- output: update the coverage view in place by default

Default mode is dry-run. Use --live --confirm-live-api to spend SerpAPI quota.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from venue_serpapi import _serpapi_request


DEFAULT_LABEL_FILE = Path("../output/venue_label_status_coverage_view.csv")
DEFAULT_OUTPUT_FILE = Path("../output/venue_label_status_coverage_view.csv")


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def load_validation_targets(label_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = pd.read_csv(label_file)
    target = labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"] == "search_matched_unvalidated")
        & labels["serpapi_place_id"].notna()
    ].copy()
    places = target.drop_duplicates("serpapi_place_id", keep="first").copy()
    return labels, places


def validate_place(
    place_id: str,
    api_key: str,
    output_dir: Path,
) -> tuple[dict[str, Any], bool]:
    params = {
        "place_id": place_id,
        "type": "place",
        "hl": "en",
    }
    cache_file = get_serpapi_cache_file(
        params=params,
        output_dir=output_dir,
        cache_prefix="healthcare_search_matched_place",
    )
    cache_hit = cache_file.exists()
    data = _serpapi_request(
        params,
        api_key,
        output_dir,
        cache_prefix="healthcare_search_matched_place",
    )
    place = (data or {}).get("place_results") or {}
    return {
        "serpapi_place_id": place_id,
        "place_title": place.get("title"),
        "has_popular_times": place.get("popular_times") is not None,
        "rating": place.get("rating"),
        "reviews": place.get("reviews"),
    }, cache_hit


def get_serpapi_cache_file(
    params: dict[str, Any],
    output_dir: Path,
    cache_prefix: str,
) -> Path:
    """Mirror venue_serpapi._serpapi_request cache key generation."""
    import hashlib
    import json

    cache_params = dict(params)
    cache_params["engine"] = "google_maps"
    cache_key = hashlib.md5(
        json.dumps(cache_params, sort_keys=True).encode()
    ).hexdigest()[:12]
    return output_dir / "serpapi_raw_responses" / f"{cache_prefix}_{cache_key}.json"


def apply_place_results(
    labels: pd.DataFrame,
    place_results: list[dict[str, Any]],
) -> pd.DataFrame:
    result_by_place = {
        item["serpapi_place_id"]: item
        for item in place_results
    }
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mask = (
        labels["venue_type"].eq("healthcare")
        & labels["label_status"].eq("search_matched_unvalidated")
        & labels["serpapi_place_id"].isin(result_by_place)
    )

    for index, row in labels[mask].iterrows():
        result = result_by_place[row["serpapi_place_id"]]
        has_popular_times = bool(result["has_popular_times"])
        labels.at[index, "label_status"] = "has_popular_times" if has_popular_times else "no_popular_times"
        labels.at[index, "ml_eligible"] = has_popular_times
        labels.at[index, "prediction_source"] = "ml_model" if has_popular_times else "rule_fallback"
        labels.at[index, "display_level"] = "quiet" if has_popular_times else "no_data"
        labels.at[index, "serpapi_checked_at"] = checked_at
        labels.at[index, "review_count"] = result.get("reviews")
        labels.at[index, "rating"] = result.get("rating")
        labels.at[index, "notes"] = "Validated by SerpAPI Place API from search_matched_unvalidated"
    return labels


def run_validation(
    label_file: Path,
    output_file: Path,
    max_place_calls: int | None,
    dry_run: bool,
    confirm_live_api: bool,
    sleep_s: float,
) -> pd.DataFrame:
    labels, places = load_validation_targets(label_file)
    if max_place_calls is not None:
        places = places.head(max_place_calls).copy()

    print(f"Input label file: {label_file}")
    print(f"Output label file: {output_file}")
    target_count = len(labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"] == "search_matched_unvalidated")
    ])
    unique_place_count = len(places)
    duplicate_saved = target_count - unique_place_count
    output_dir = output_file.parent
    planned_cache_hits = 0
    for place_id in places["serpapi_place_id"].dropna().astype(str):
        cache_file = get_serpapi_cache_file(
            params={"place_id": place_id, "type": "place", "hl": "en"},
            output_dir=output_dir,
            cache_prefix="healthcare_search_matched_place",
        )
        planned_cache_hits += int(cache_file.exists())
    planned_live_calls = unique_place_count - planned_cache_hits

    print(f"Target search_matched_unvalidated venues: {target_count}")
    print(f"Unique place_id to validate: {unique_place_count}")
    print(f"Duplicate venue rows saved by place_id dedupe: {duplicate_saved}")
    print(f"Cached Place responses available: {planned_cache_hits}")
    print(f"Estimated new live Place API calls: {planned_live_calls}")

    if dry_run:
        print("Dry-run only. No SerpAPI calls will be made.")
        preview_cols = ["venue_id", "venue_name", "district", "serpapi_place_id"]
        available_preview_cols = [col for col in preview_cols if col in places.columns]
        print(places[available_preview_cols].head(20).to_string(index=False))
        return labels

    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required for live API runs.")

    output_dir.mkdir(parents=True, exist_ok=True)
    place_results: list[dict[str, Any]] = []
    attempted_place_calls = 0
    cache_hits = 0
    live_calls = 0

    for index, (_, place_row) in enumerate(places.iterrows(), start=1):
        place_id = str(place_row["serpapi_place_id"])
        print(f"[{index}/{len(places)}] Place API: {place_row.get('venue_name', place_id)}")
        result, cache_hit = validate_place(place_id, api_key, output_dir)
        attempted_place_calls += 1
        cache_hits += int(cache_hit)
        live_calls += int(not cache_hit)
        place_results.append(result)
        time.sleep(sleep_s)

    updated = apply_place_results(labels, place_results)
    updated.to_csv(output_file, index=False)

    healthcare = updated[updated["venue_type"] == "healthcare"]
    remaining_unvalidated = int(
        healthcare["label_status"].eq("search_matched_unvalidated").sum()
    )
    print("\nValidation complete")
    print(f"Unique Place API validations attempted: {attempted_place_calls}")
    print(f"Cache hits: {cache_hits}")
    print(f"New live Place API calls: {live_calls}")
    print(f"Venue rows updated from validation: {target_count - remaining_unvalidated}")
    print(f"Remaining search_matched_unvalidated venues: {remaining_unvalidated}")
    print("Healthcare label_status after validation:")
    print(healthcare["label_status"].value_counts().to_string())
    return updated


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate search-matched healthcare places with SerpAPI Place API."
    )
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--max-place-calls", type=int, default=None)
    parser.add_argument("--sleep-s", type=float, default=0.5)
    parser.add_argument("--confirm-live-api", action="store_true")
    parser.add_argument("--live", action="store_true", help="Disable dry-run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    run_validation(
        label_file=resolve_path(args.label_file),
        output_file=resolve_path(args.output_file),
        max_place_calls=args.max_place_calls,
        dry_run=not args.live,
        confirm_live_api=args.confirm_live_api,
        sleep_s=args.sleep_s,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

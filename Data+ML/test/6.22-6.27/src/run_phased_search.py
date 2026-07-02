"""Phased DB-driven Search + Place API for 500-call budget.

Phase A: Stratified DB-driven Search only (find place_ids)
Phase B: Place API on unique serpapi_place_id (check popular_times)
Usage:
  python run_phased_search.py --phase A --budget 250 --live --confirm-live-api
  python run_phased_search.py --phase B --live --confirm-live-api
  python run_phased_search.py --phase merge
  python run_phased_search.py --phase summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from api_usage_tracker import ApiUsageTracker
from geo_utils import haversine_distance_m
from serpapi_client import get_cache_path, serpapi_request as _serpapi_request


# ── Subtype classification ──────────────────────────────────────

PHARMACY_KW = ["pharmacy", "pharm", "drug", "cvs", "walgreens", "duane", "rite aid"]
HOSPITAL_KW = ["hospital", "medical center", "medical ctr", "health center", "health ctr"]
DENTIST_KW = ["dental", "dentist", "dds", "dmd", "oral"]
DQR_SUBTYPE_ALLOCATION = {
    "clinic": 129,
    "pharmacy": 65,
    "hospital": 34,
    "dentist": 22,
}

# Priority: core Manhattan districts
CORE_DISTRICTS = {"downtown", "midtown_east", "midtown_west"}


def classify_subtype(name: str) -> str:
    """Classify venue into the four DQR healthcare categories."""
    lower = name.lower()
    if any(k in lower for k in PHARMACY_KW):
        return "pharmacy"
    if any(k in lower for k in HOSPITAL_KW):
        return "hospital"
    if any(k in lower for k in DENTIST_KW):
        return "dentist"
    return "clinic"


def priority_score(row: pd.Series) -> float:
    """Higher = better candidate for Search."""
    score = 0.0
    # Core district bonus
    if row.get("district") in CORE_DISTRICTS:
        score += 2.0
    # Name quality: longer = clearer
    name_len = len(str(row.get("name", "")))
    if name_len > 15:
        score += 1.5
    elif name_len > 8:
        score += 1.0
    elif name_len <= 4:
        score -= 1.0
    # Subtype priority
    subtype = classify_subtype(str(row.get("name", "")))
    subtype_bonus = {"pharmacy": 1.5, "hospital": 1.0, "dentist": 0.8, "clinic": 0.5}
    score += subtype_bonus.get(subtype, 0.0)
    return score


def is_true(value: Any) -> bool:
    """Parse booleans safely from pandas values and CSV strings."""
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def get_search_candidates(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize SerpAPI Search responses into comparable place candidates."""
    local_results = data.get("local_results") or []
    if local_results:
        return list(local_results[:5])

    place_results = data.get("place_results")
    if isinstance(place_results, dict):
        return [place_results]

    return []


# ── Stratified sampling ─────────────────────────────────────────

def stratified_sample(
    unmatched: pd.DataFrame,
    budget: int,
) -> pd.DataFrame:
    """Stratified sample by fixed DQR healthcare subtype allocation."""
    unmatched = unmatched.copy()
    unmatched["_subtype"] = unmatched["name"].apply(classify_subtype)
    unmatched["_priority"] = unmatched.apply(priority_score, axis=1)

    scale = budget / sum(DQR_SUBTYPE_ALLOCATION.values())
    allocation = {
        subtype: int(round(target * scale))
        for subtype, target in DQR_SUBTYPE_ALLOCATION.items()
    }
    diff = budget - sum(allocation.values())
    if diff:
        allocation["clinic"] += diff

    sampled = []
    shortage = 0
    for subtype, target in allocation.items():
        pool = unmatched[unmatched["_subtype"] == subtype].sort_values("_priority", ascending=False)
        take = min(target, len(pool))
        sampled.append(pool.head(take))
        shortage += target - take

    if shortage > 0:
        selected_ids = set(pd.concat(sampled)["venue_id"].astype(str)) if sampled else set()
        remainder = unmatched[
            ~unmatched["venue_id"].astype(str).isin(selected_ids)
        ].sort_values("_priority", ascending=False)
        sampled.append(remainder.head(shortage))

    result = pd.concat(sampled).sort_values("_priority", ascending=False)
    return result.head(budget)


# ── Phase A: Search only ────────────────────────────────────────

def run_phase_a(
    label_file: Path,
    output_dir: Path,
    budget: int,
    batch_size: int,
    match_radius_m: float,
    min_name_similarity: float,
    sleep_s: float,
    dry_run: bool,
    confirm_live_api: bool,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """Phase A: DB-driven Search only, no Place API."""
    print(f"=== Phase A: DB-driven Search (budget={budget}) ===")

    labels = pd.read_csv(label_file)
    unmatched = labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"] == "search_not_matched")
    ].copy()

    # Skip already-processed venues
    prior_file = output_dir / "phase_a_search_results.csv"
    if prior_file.exists() and not dry_run and skip_existing:
        prior = pd.read_csv(prior_file, usecols=["venue_id"])
        done_ids = set(prior["venue_id"].dropna().astype(str))
        unmatched = unmatched[~unmatched["venue_id"].astype(str).isin(done_ids)]
        print(f"  Skipping {len(done_ids)} already-processed venues")

    # Stratified sample
    sample = stratified_sample(unmatched, budget)
    print(f"  Input pool: {len(unmatched)} unmatched")
    print(f"  Sample selected: {len(sample)}")

    # Show subtype distribution
    sample["_subtype"] = sample["name"].apply(classify_subtype)
    print("  Subtype distribution:")
    for st, cnt in sample["_subtype"].value_counts().items():
        print(f"    {st}: {cnt}")

    if dry_run:
        print("\n  Dry-run only. No API calls.")
        cols = ["venue_id", "name", "district", "latitude", "longitude"]
        print(sample[cols].head(20).to_string(index=False))
        return sample

    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required.")

    tracker = ApiUsageTracker(output_dir, run_id=f"phase_a_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M')}")
    rows: list[dict[str, Any]] = []

    for idx, (_, venue) in enumerate(sample.iterrows(), start=1):
        print(f"  [{idx}/{len(sample)}] Search: {venue['name'][:50]}")

        params = {
            "q": str(venue["name"]),
            "ll": f"@{float(venue['latitude'])},{float(venue['longitude'])},18z",
            "type": "search",
            "hl": "en",
            "gl": "us",
        }
        cache_hit = get_cache_path(output_dir, "phase_a_search", params).exists()

        data = _serpapi_request(params, api_key, output_dir, cache_prefix="phase_a_search")

        if not data:
            tracker.log_search_call(
                query=str(venue["name"]),
                district=str(venue.get("district", "")),
                category=classify_subtype(str(venue["name"])),
                success=False,
            )
            rows.append({
                "venue_id": venue["venue_id"],
                "venue_name": venue["name"],
                "district": venue.get("district"),
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
                "subtype": classify_subtype(str(venue["name"])),
                "cache_hit": cache_hit,
                "results_count": 0,
                "matched": False,
                "serpapi_place_id": None,
                "serpapi_name": None,
                "distance_m": None,
                "name_similarity": None,
            })
            time.sleep(sleep_s)
            continue

        search_candidates = get_search_candidates(data)
        results_count = len(search_candidates)
        best_match = None
        best_distance = float("inf")

        for result in search_candidates:
            gps = result.get("gps_coordinates") or {}
            r_lat = gps.get("latitude")
            r_lng = gps.get("longitude")
            if r_lat is None or r_lng is None:
                continue

            dist = haversine_distance_m(
                float(venue["latitude"]), float(venue["longitude"]),
                float(r_lat), float(r_lng),
            )

            if dist <= match_radius_m and dist < best_distance:
                # Name similarity
                from difflib import SequenceMatcher
                norm_v = " ".join(str(venue["name"]).lower().split())
                norm_r = " ".join(str(result.get("title", "")).lower().split())
                sim = SequenceMatcher(None, norm_v, norm_r).ratio()
                if sim >= min_name_similarity:
                    best_match = result
                    best_distance = dist
                    best_sim = sim

        if best_match:
            tracker.log_search_call(
                query=str(venue["name"]),
                district=str(venue.get("district", "")),
                category=classify_subtype(str(venue["name"])),
                success=True,
                matched_venues=1,
            )
            rows.append({
                "venue_id": venue["venue_id"],
                "venue_name": venue["name"],
                "district": venue.get("district"),
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
                "subtype": classify_subtype(str(venue["name"])),
                "cache_hit": cache_hit,
                "results_count": results_count,
                "matched": True,
                "serpapi_place_id": best_match.get("place_id"),
                "serpapi_data_id": best_match.get("data_id"),
                "serpapi_name": best_match.get("title"),
                "serpapi_type": best_match.get("type"),
                "distance_m": round(best_distance, 3),
                "name_similarity": round(best_sim, 4),
                "reviews": best_match.get("reviews"),
                "rating": best_match.get("rating"),
            })
        else:
            tracker.log_search_call(
                query=str(venue["name"]),
                district=str(venue.get("district", "")),
                category=classify_subtype(str(venue["name"])),
                success=True,
                matched_venues=0,
            )
            rows.append({
                "venue_id": venue["venue_id"],
                "venue_name": venue["name"],
                "district": venue.get("district"),
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
                "subtype": classify_subtype(str(venue["name"])),
                "cache_hit": cache_hit,
                "results_count": results_count,
                "matched": False,
                "serpapi_place_id": None,
                "serpapi_name": None,
                "distance_m": None,
                "name_similarity": None,
            })

        time.sleep(sleep_s)

    # Save results
    result_df = pd.DataFrame(rows)
    if prior_file.exists():
        existing = pd.read_csv(prior_file)
        result_df = pd.concat([existing, result_df], ignore_index=True)
        result_df = result_df.drop_duplicates(subset="venue_id", keep="last")
    result_df.to_csv(prior_file, index=False)

    tracker.print_summary("Phase A Search")
    tracker.save()

    # Print dedup stats
    matched = result_df[result_df["matched"] == True]
    unique_places = matched["serpapi_place_id"].dropna().nunique()
    print(f"\n  Matched venues: {len(matched)}")
    print(f"  Unique serpapi_place_ids: {unique_places}")
    print(f"  → Phase B Place API calls needed: {unique_places}")

    return result_df


# ── Phase B: Place API on unique place_ids ──────────────────────

def run_phase_b(
    search_results_file: Path,
    label_file: Path,
    output_dir: Path,
    match_radius_m: float,
    sleep_s: float,
    dry_run: bool,
    confirm_live_api: bool,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """Phase B: Place API on unique serpapi_place_ids from Phase A."""
    print(f"=== Phase B: Place API validation ===")

    search_results = pd.read_csv(search_results_file)
    matched = search_results[search_results["matched"].apply(is_true)].copy()
    matched = matched[matched["serpapi_place_id"].notna()]

    # Deduplicate by serpapi_place_id, keep first match per place
    unique_places = matched.drop_duplicates(subset="serpapi_place_id", keep="first")
    print(f"  Search results: {len(matched)} matched venues")
    print(f"  Unique place_ids: {len(unique_places)}")

    # Skip already-validated
    prior_file = output_dir / "phase_b_place_results.csv"
    if prior_file.exists() and not dry_run and skip_existing:
        prior = pd.read_csv(prior_file, usecols=["serpapi_place_id"])
        done_places = set(prior["serpapi_place_id"].dropna().astype(str))
        unique_places = unique_places[~unique_places["serpapi_place_id"].astype(str).isin(done_places)]
        print(f"  Skipping {len(done_places)} already-validated place_ids")

    if dry_run:
        print("\n  Dry-run only. No API calls.")
        print(f"  Place IDs to validate: {len(unique_places)}")
        cols = ["venue_id", "venue_name", "serpapi_place_id", "serpapi_name", "distance_m"]
        print(unique_places[cols].head(20).to_string(index=False))
        return unique_places

    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required.")

    tracker = ApiUsageTracker(output_dir, run_id=f"phase_b_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M')}")
    rows: list[dict[str, Any]] = []

    for idx, (_, row) in enumerate(unique_places.iterrows(), start=1):
        place_id = str(row["serpapi_place_id"])
        print(f"  [{idx}/{len(unique_places)}] Place: {row['venue_name'][:40]} ({place_id[:20]}...)")

        params = {
            "place_id": place_id,
            "type": "place",
            "hl": "en",
        }
        cache_hit = get_cache_path(output_dir, "phase_b_place", params).exists()

        data = _serpapi_request(params, api_key, output_dir, cache_prefix="phase_b_place")

        has_popular_times = False
        place_results = {}
        if data and "place_results" in data:
            place_results = data["place_results"] or {}
            has_popular_times = place_results.get("popular_times") is not None

        tracker.log_place_call(
            place_id=place_id,
            venue_name=str(row["venue_name"]),
            success=data is not None,
            has_popular_times=has_popular_times,
            venue_id=str(row["venue_id"]),
        )

        result_row = {
            "venue_id": row["venue_id"],
            "venue_name": row["venue_name"],
            "district": row.get("district"),
            "serpapi_place_id": place_id,
            "serpapi_name": row.get("serpapi_name"),
            "distance_m": row.get("distance_m"),
            "cache_hit": cache_hit,
            "reviews": place_results.get("reviews", row.get("reviews")),
            "rating": place_results.get("rating", row.get("rating")),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "has_popular_times": has_popular_times,
            "label_status": "has_popular_times" if has_popular_times else "no_popular_times",
        }
        rows.append(result_row)

        time.sleep(sleep_s)

    result_df = pd.DataFrame(rows)
    if prior_file.exists():
        existing = pd.read_csv(prior_file)
        result_df = pd.concat([existing, result_df], ignore_index=True)
        result_df = result_df.drop_duplicates(subset="serpapi_place_id", keep="last")
    result_df.to_csv(prior_file, index=False)

    tracker.print_summary("Phase B Place")
    tracker.save()

    new_has_pt = sum(1 for r in rows if r["has_popular_times"])
    new_no_pt = len(rows) - new_has_pt
    print(f"\n  new has_popular_times: {new_has_pt}")
    print(f"  new no_popular_times: {new_no_pt}")
    print(f"  hit rate: {new_has_pt}/{len(rows)} ({new_has_pt/len(rows)*100:.1f}%)" if rows else "  hit rate: N/A")

    apply_phase_results_to_coverage(label_file, search_results_file, prior_file)

    return result_df


# ── Merge results back to coverage view ────────────────────────

def apply_phase_results_to_coverage(
    label_file: Path,
    search_results_file: Path,
    place_results_file: Path,
) -> pd.DataFrame:
    """Merge Phase A/B outputs back into venue_label_status_coverage_view.csv."""
    labels = pd.read_csv(label_file)
    search = pd.read_csv(search_results_file)
    place = pd.read_csv(place_results_file) if place_results_file.exists() else pd.DataFrame()

    place_by_id: dict[str, pd.Series] = {}
    if not place.empty:
        place_by_id = {
            str(row["serpapi_place_id"]): row
            for _, row in place.iterrows()
            if pd.notna(row.get("serpapi_place_id"))
        }

    now = datetime.now(timezone.utc).isoformat()
    updated_has = 0
    updated_no = 0
    updated_pending = 0

    labels = labels.copy()
    labels["_venue_id_key"] = labels["venue_id"].astype(str)

    for _, row in search.iterrows():
        if not is_true(row.get("matched")):
            continue

        venue_id = str(row.get("venue_id"))
        mask = labels["_venue_id_key"] == venue_id
        if not mask.any():
            continue

        place_id = str(row.get("serpapi_place_id")) if pd.notna(row.get("serpapi_place_id")) else ""
        labels.loc[mask, "serpapi_place_id"] = place_id or np.nan
        labels.loc[mask, "serpapi_checked_at"] = now
        labels.loc[mask, "review_count"] = row.get("reviews")
        labels.loc[mask, "rating"] = row.get("rating")

        if place_id and place_id in place_by_id:
            p = place_by_id[place_id]
            has_pt = bool(p.get("has_popular_times"))
            status = "has_popular_times" if has_pt else "no_popular_times"
            labels.loc[mask, "label_status"] = status
            labels.loc[mask, "ml_eligible"] = has_pt
            labels.loc[mask, "prediction_source"] = "ml_model" if has_pt else "rule_fallback"
            labels.loc[mask, "display_level"] = "quiet" if has_pt else "no_data"
            labels.loc[mask, "review_count"] = p.get("reviews", row.get("reviews"))
            labels.loc[mask, "rating"] = p.get("rating", row.get("rating"))
            labels.loc[mask, "notes"] = (
                "Matched by DB-driven SerpAPI Search; "
                f"Place API validated as {status}"
            )
            updated_has += int(has_pt)
            updated_no += int(not has_pt)
        else:
            labels.loc[mask, "label_status"] = "search_matched_unvalidated"
            labels.loc[mask, "ml_eligible"] = False
            labels.loc[mask, "prediction_source"] = "pending_place_validation"
            labels.loc[mask, "display_level"] = "no_data"
            labels.loc[mask, "notes"] = (
                "Matched by DB-driven SerpAPI Search; "
                "Place API validation pending"
            )
            updated_pending += 1

    labels = labels.drop(columns=["_venue_id_key"])
    labels.to_csv(label_file, index=False)

    print("\n=== Coverage merge complete ===")
    print(f"  Updated has_popular_times: {updated_has}")
    print(f"  Updated no_popular_times: {updated_no}")
    print(f"  Updated search_matched_unvalidated: {updated_pending}")
    print(f"  Coverage file: {label_file}")

    return labels


# ── CLI ─────────────────────────────────────────────────────────

DEFAULT_LABEL_FILE = Path("../output/venue_label_status_coverage_view.csv")
DEFAULT_OUTPUT_DIR = Path("../output")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phased DB-driven Search + Place for 500-call budget.")
    parser.add_argument("--phase", choices=["A", "B", "merge", "summary"], required=True)
    parser.add_argument("--budget", type=int, default=250, help="Search call budget for Phase A")
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--match-radius-m", type=float, default=200)
    parser.add_argument("--min-name-similarity", type=float, default=0.4)
    parser.add_argument("--quota", type=int, default=500)
    parser.add_argument("--sleep-s", type=float, default=1.0)
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--confirm-live-api", action="store_true")
    parser.add_argument("--live", action="store_true", help="Disable dry-run.")
    return parser.parse_args(argv)


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def run_summary(output_dir: Path, quota: int = 500) -> None:
    """Print summary of all phases."""
    print("=== Phase Summary ===\n")

    db_search_attempted = 0
    search_matched_count = 0
    unique_place_id_count = 0
    search_cache_hits = 0
    search_live_calls = 0
    place_api_calls = 0
    place_cache_hits = 0
    place_live_calls = 0
    new_has_popular_times = 0
    new_no_popular_times = 0

    # Phase A
    phase_a_file = output_dir / "phase_a_search_results.csv"
    if phase_a_file.exists():
        a = pd.read_csv(phase_a_file)
        matched = a[a["matched"].apply(is_true)]
        db_search_attempted = len(a)
        search_matched_count = len(matched)
        unique_place_id_count = matched["serpapi_place_id"].dropna().nunique()
        if "cache_hit" in a.columns:
            search_cache_hits = int(a["cache_hit"].fillna(False).astype(bool).sum())
        search_live_calls = db_search_attempted - search_cache_hits
        print(f"Phase A (Search):")
        print(f"  Total searched: {db_search_attempted}")
        print(f"  Matched: {search_matched_count}")
        print(f"  Unique place_ids: {unique_place_id_count}")
        print(f"  Search cache hits: {search_cache_hits}")
        print(f"  Search live calls: {search_live_calls}")
        print(f"  By subtype:")
        for st, cnt in a["subtype"].value_counts().items():
            print(f"    {st}: {cnt}")
        print()

    # Phase B
    phase_b_file = output_dir / "phase_b_place_results.csv"
    if phase_b_file.exists():
        b = pd.read_csv(phase_b_file)
        has_pt = b[b["has_popular_times"] == True]
        place_api_calls = len(b)
        if "cache_hit" in b.columns:
            place_cache_hits = int(b["cache_hit"].fillna(False).astype(bool).sum())
        place_live_calls = place_api_calls - place_cache_hits
        new_has_popular_times = len(has_pt)
        new_no_popular_times = len(b) - len(has_pt)
        print(f"Phase B (Place):")
        print(f"  Total validated: {place_api_calls}")
        print(f"  has_popular_times: {new_has_popular_times}")
        print(f"  no_popular_times: {new_no_popular_times}")
        print(f"  Place cache hits: {place_cache_hits}")
        print(f"  Place live calls: {place_live_calls}")
        if len(b) > 0:
            print(f"  hit rate: {len(has_pt)}/{len(b)} ({len(has_pt)/len(b)*100:.1f}%)")
        print()

    new_labels = new_has_popular_times + new_no_popular_times
    new_live_api_calls = search_live_calls + place_live_calls
    print("Plan Metrics:")
    print(f"  db_search_attempted: {db_search_attempted}")
    print(f"  search_matched_count: {search_matched_count}")
    print(f"  unique_place_id_count: {unique_place_id_count}")
    print(f"  place_api_calls: {place_api_calls}")
    print(f"  cache_hits: {search_cache_hits + place_cache_hits}")
    print(f"  new_live_api_calls: {new_live_api_calls}")
    print(f"  new_has_popular_times: {new_has_popular_times}")
    print(f"  new_no_popular_times: {new_no_popular_times}")
    print(f"  api_calls_per_new_label: {round(new_live_api_calls / new_labels, 2) if new_labels else 'N/A'}")
    print(f"  remaining_quota_estimate: {quota - new_live_api_calls}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output_dir = resolve_path(args.output_dir)
    label_file = resolve_path(args.label_file)
    dry_run = not args.live

    if args.phase == "summary":
        run_summary(output_dir, quota=args.quota)
        return 0

    if args.phase == "A":
        run_phase_a(
            label_file=resolve_path(args.label_file),
            output_dir=output_dir,
            budget=args.budget,
            batch_size=args.budget,
            match_radius_m=args.match_radius_m,
            min_name_similarity=args.min_name_similarity,
            sleep_s=args.sleep_s,
            dry_run=dry_run,
            confirm_live_api=args.confirm_live_api,
            skip_existing=not args.no_skip_existing,
        )
    elif args.phase == "B":
        search_results_file = output_dir / "phase_a_search_results.csv"
        if not search_results_file.exists():
            raise SystemExit(f"Phase A results not found: {search_results_file}\nRun Phase A first.")
        run_phase_b(
            search_results_file=search_results_file,
            label_file=label_file,
            output_dir=output_dir,
            match_radius_m=args.match_radius_m,
            sleep_s=args.sleep_s,
            dry_run=dry_run,
            confirm_live_api=args.confirm_live_api,
            skip_existing=not args.no_skip_existing,
        )
    elif args.phase == "merge":
        search_results_file = output_dir / "phase_a_search_results.csv"
        place_results_file = output_dir / "phase_b_place_results.csv"
        if not search_results_file.exists():
            raise SystemExit(f"Phase A results not found: {search_results_file}")
        apply_phase_results_to_coverage(label_file, search_results_file, place_results_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

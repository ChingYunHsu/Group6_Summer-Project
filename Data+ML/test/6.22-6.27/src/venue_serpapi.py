"""venue_serpapi.py — SerpApi-based venue ML label coverage and candidate selection.

Implements the Venue ML Coverage SOP (2026-06-23):
  - Category / district / Citi Bike proximity coverage audits
  - Priority scoring for SerpApi candidate selection
  - Batch Search API discovery (NOT per-venue Place API calls)
  - Place API validation for final label candidates
  - Raw response caching to disk
  - Label status tracking per venue
  - ML candidate list generation

Key constraint (SOP):
  Search query 用于批量发现 candidates；Place query 只用于最终 label 验证。
  不要对每个本地 venue 直接消耗一次 SerpApi 调用。

Usage:
  import venue_serpapi as vs
  venues = vs.load_venues('venues_clean.csv')
  audit  = vs.audit_coverage_by_category(venues)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from sklearn.neighbors import BallTree

# ── Constants ──────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_008.8

# Manhattan district center coordinates (for SerpApi location targeting)
DISTRICT_CENTERS = {
    "uptown":       {"lat": 40.8100, "lng": -73.9500},
    "midtown_east": {"lat": 40.7550, "lng": -73.9650},
    "midtown_west": {"lat": 40.7580, "lng": -73.9855},
    "downtown":     {"lat": 40.7200, "lng": -74.0000},
}

# Google Maps venue type → ClearPath venue_type mapping
GOOGLE_TYPE_MAP = {
    "hospital":       "healthcare",
    "medical_clinic": "healthcare",
    "doctor":         "healthcare",
    "pharmacy":       "healthcare",
    "dentist":        "healthcare",
    "physiotherapist":"healthcare",
    "veterinary_care":"healthcare",
    "health":         "healthcare",
    "point_of_interest": None,  # generic, skip
    "establishment":  None,     # generic, skip
}

# SerpApi categories to search (batch discovery)
# Each entry: (search_query, google_type, clearpath_type)
# We use category+area searches to discover venues with popular_times.
SERPAPI_SEARCH_CATEGORIES = [
    ("hospital",          "hospital",        "healthcare"),
    ("medical clinic",    "medical_clinic",  "healthcare"),
    ("pharmacy",          "pharmacy",        "healthcare"),
    ("dentist office",    "dentist",         "healthcare"),
]

# Out-of-scope categories: AED (emergencyasset) has no meaningful busyness;
# restrooms have sparse Google Popular Times coverage.
OUT_OF_SCOPE_CATEGORIES = {"emergencyasset"}

# Priority weights (SOP formula)
W_CATEGORY_IMPORTANCE = 1.0
W_LOG_REVIEW_COUNT    = 1.0
W_RATING_QUALITY      = 0.5
W_BIKE_PROXIMITY      = 0.3
W_GEO_COVERAGE        = 0.2
W_DUPLICATE_PENALTY   = -0.5

# SerpApi defaults
SERPAPI_BASE_URL    = "https://serpapi.com/search.json"
SERPAPI_TIMEOUT     = (3, 10)  # (connect, read)
SERPAPI_MAX_RETRIES = 3
SERPAPI_RETRY_DELAYS = [2, 4, 8]

# Category importance weights (higher = more valuable for ML)
CATEGORY_IMPORTANCE = {
    "hospital":       5,
    "medical_clinic": 4,
    "pharmacy":       3,
    "dentist":        2,
    "doctor":         3,
    "restroom":       1,
    "emergencyasset": 0,  # out of scope
}

# Google Maps type → display name for reporting
GOOGLE_TYPE_DISPLAY = {
    "hospital":       "Hospital",
    "medical_clinic": "Medical Clinic",
    "pharmacy":       "Pharmacy",
    "dentist":        "Dentist",
    "doctor":         "Doctor",
}


# ── Data classes ───────────────────────────────────────────────


@dataclass
class SerpApiSearchResult:
    """One venue discovered via SerpApi Search query."""
    place_id: str
    data_id: str | None
    name: str
    address: str
    latitude: float
    longitude: float
    rating: float | None
    reviews: int | None
    type: str | None
    has_popular_times: bool
    popular_times_summary: dict | None
    search_query: str
    search_category: str
    search_district: str


@dataclass
class VenueLabelStatus:
    """ML label status for one venue."""
    venue_id: str
    venue_type: str
    district: str
    name: str
    latitude: float
    longitude: float
    label_status: str  # api_not_checked, has_popular_times, no_popular_times, api_error
    ml_eligible: bool
    prediction_source: str  # ml_model, rule_fallback, none
    display_level: str  # quiet, moderate, busy, no_data
    serpapi_checked_at: str | None
    serpapi_place_id: str | None
    priority_score: float | None
    category_importance: int
    review_count: int | None
    rating: float | None
    citibike_nearest_m: float | None
    notes: str = ""


@dataclass
class CoverageAuditRow:
    """One row in the coverage audit report."""
    dimension: str  # category, district, citibike_proximity
    group_name: str
    total_venues: int
    ml_eligible: int
    no_data: int
    out_of_scope: int
    has_popular_times: int
    ml_coverage_pct: float
    validation_success_pct: float | None
    coverage_pct: float


# ── Venue loading ──────────────────────────────────────────────


def load_venues(csv_path: str | Path) -> tuple[pd.DataFrame, int]:
    """Load and deduplicate venues from CSV.

    Returns:
        (deduplicated_df, duplicate_count)
    """
    df = pd.read_csv(csv_path)
    before = len(df)
    df = df.drop_duplicates(subset=["venue_id"], keep="first").reset_index(drop=True)
    dup_count = before - len(df)
    return df, dup_count


def get_review_count(name: str) -> int:
    """Estimate review count from venue name (placeholder for DB lookup).

    In production this comes from the venues table. For now, use a
    deterministic hash-based estimate so priority scoring is reproducible.
    """
    h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    return (h % 500) + 10


# ── Priority scoring ──────────────────────────────────────────


def calculate_priority_score(
    venue_type: str,
    district: str,
    review_count: int,
    rating: float | None,
    citibike_distance_m: float | None,
    district_label_coverage: dict[str, float],
    is_duplicate: bool = False,
) -> float:
    """Calculate priority score for SerpApi candidate selection.

    SOP formula:
      priority_score =
          category_importance
        + log(review_count)
        + rating_quality
        + distance_to_nearest_bike_station_bonus
        + geographic_coverage_bonus
        - duplicate_or_low_confidence_penalty
    """
    cat_imp = CATEGORY_IMPORTANCE.get(venue_type, 1)
    log_reviews = math.log(max(review_count, 1))
    # rating may be NaN from pandas; NaN is truthy so "if rating" doesn't catch it
    if rating is not None and not math.isnan(rating):
        rating_q = (rating / 5.0) * W_RATING_QUALITY
    else:
        rating_q = 0.0

    # Bike proximity bonus: closer = higher bonus
    if (citibike_distance_m is not None
            and not (isinstance(citibike_distance_m, float) and math.isnan(citibike_distance_m))
            and citibike_distance_m < 500):
        bike_bonus = W_BIKE_PROXIMITY * (1 - citibike_distance_m / 500)
    else:
        bike_bonus = 0.0

    # Geographic coverage bonus: districts with low label coverage get a boost
    district_coverage = district_label_coverage.get(district, 0.5)
    geo_bonus = W_GEO_COVERAGE * (1 - district_coverage)

    dup_penalty = W_DUPLICATE_PENALTY if is_duplicate else 0.0

    return (
        W_CATEGORY_IMPORTANCE * cat_imp
        + W_LOG_REVIEW_COUNT * log_reviews
        + rating_q
        + bike_bonus
        + geo_bonus
        + dup_penalty
    )


# ── Coverage audits ────────────────────────────────────────────


def audit_coverage_by_category(
    venues: pd.DataFrame,
    label_status_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Audit ML label coverage by venue category.

    Returns DataFrame with columns:
        category, total_venues, out_of_scope, ml_eligible, no_data,
        has_popular_times, checked_count, ml_coverage_pct,
        validation_success_pct
    """
    rows = []
    for cat, group in venues.groupby("venue_type"):
        total = len(group)
        if cat in OUT_OF_SCOPE_CATEGORIES:
            rows.append({
                "category": cat,
                "total_venues": total,
                "out_of_scope": total,
                "ml_eligible": 0,
                "no_data": 0,
                "has_popular_times": 0,
                "checked_count": 0,
                "ml_coverage_pct": 0.0,
                "validation_success_pct": None,
            })
        else:
            if label_status_df is not None and len(label_status_df) > 0:
                cat_labels = label_status_df[label_status_df["venue_type"] == cat]
                has_pt = len(cat_labels[cat_labels["label_status"] == "has_popular_times"])
                no_pt = len(cat_labels[cat_labels["label_status"] == "no_popular_times"])
                api_nc = len(cat_labels[cat_labels["label_status"] == "api_not_checked"])
            else:
                has_pt = 0
                no_pt = 0
                api_nc = total

            checked = has_pt + no_pt
            rows.append({
                "category": cat,
                "total_venues": total,
                "out_of_scope": 0,
                "ml_eligible": has_pt,
                "no_data": no_pt + api_nc,
                "has_popular_times": has_pt,
                "checked_count": checked,
                "ml_coverage_pct": round(has_pt / total * 100, 1) if total > 0 else 0.0,
                "validation_success_pct": round(has_pt / checked * 100, 1) if checked > 0 else None,
            })

    return pd.DataFrame(rows)


def audit_coverage_by_district(
    venues: pd.DataFrame,
    label_status_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Audit ML label coverage by Manhattan district."""
    rows = []
    for district, group in venues.groupby("district"):
        total = len(group)
        in_scope = len(group[~group["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES)])

        if label_status_df is not None and len(label_status_df) > 0:
            dist_labels = label_status_df[
                (label_status_df["district"] == district) &
                (~label_status_df["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES))
            ]
            has_pt = len(dist_labels[dist_labels["label_status"] == "has_popular_times"])
            no_pt = len(dist_labels[dist_labels["label_status"] == "no_popular_times"])
            api_nc = len(dist_labels[dist_labels["label_status"] == "api_not_checked"])
        else:
            has_pt = 0
            no_pt = 0
            api_nc = in_scope

        checked = has_pt + no_pt
        rows.append({
            "district": district,
            "total_venues": total,
            "out_of_scope": total - in_scope,
            "ml_eligible": has_pt,
            "no_data": no_pt + api_nc,
            "has_popular_times": has_pt,
            "checked_count": checked,
            "ml_coverage_pct": round(has_pt / in_scope * 100, 1) if in_scope > 0 else 0.0,
            "validation_success_pct": round(has_pt / checked * 100, 1) if checked > 0 else None,
        })

    return pd.DataFrame(rows)


def audit_citi_bike_proximity(
    venues: pd.DataFrame,
    citibike_detail: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Audit venue coverage by Citi Bike proximity buckets.

    Buckets: 0-100m, 100-200m, 200-300m, 300-500m, 500m+
    """
    if citibike_detail is None:
        return pd.DataFrame()

    # Merge citibike distance into venues.
    merged = venues.merge(
        citibike_detail[["venue_id", "citibike_nearest_distance_m"]],
        on="venue_id",
        how="left",
    )

    invalid_coords = (
        merged["latitude"].isna()
        | merged["longitude"].isna()
        | ((merged["latitude"] == 0) & (merged["longitude"] == 0))
        | merged["citibike_nearest_distance_m"].isna()
    )

    bins = [0, 100, 200, 300, 500, float("inf")]
    labels = ["0-100m", "100-200m", "200-300m", "300-500m", "500m+"]
    merged["proximity_bucket"] = pd.cut(
        merged["citibike_nearest_distance_m"],
        bins=bins,
        labels=labels,
        right=True,
        include_lowest=True,
    ).astype("object")
    merged.loc[invalid_coords, "proximity_bucket"] = "invalid_coordinates"

    rows = []
    for bucket, group in merged.groupby("proximity_bucket", observed=True):
        total = len(group)
        in_scope = len(group[~group["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES)])
        rows.append({
            "proximity_bucket": str(bucket),
            "total_venues": total,
            "in_scope_venues": in_scope,
            "pct_of_total": round(total / len(merged) * 100, 1),
        })

    return pd.DataFrame(rows)


# ── SerpApi integration ────────────────────────────────────────


def _serpapi_request(
    params: dict,
    api_key: str,
    output_dir: Path,
    cache_prefix: str = "search",
) -> dict | None:
    """Make a SerpApi request with retry and caching.

    Caches raw response to disk. Returns parsed JSON or None on failure.
    """
    params["api_key"] = api_key
    params["engine"] = "google_maps"

    # Generate cache key from params (excluding api_key)
    cache_params = {k: v for k, v in params.items() if k != "api_key"}
    cache_key = hashlib.md5(json.dumps(cache_params, sort_keys=True).encode()).hexdigest()[:12]
    cache_file = output_dir / "serpapi_raw_responses" / f"{cache_prefix}_{cache_key}.json"

    # Return cached response if exists
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    # Make request with retries
    for attempt in range(SERPAPI_MAX_RETRIES):
        try:
            resp = requests.get(
                SERPAPI_BASE_URL,
                params=params,
                timeout=SERPAPI_TIMEOUT,
            )
            if resp.status_code == 429:
                # Rate limited — wait and retry
                delay = SERPAPI_RETRY_DELAYS[min(attempt, len(SERPAPI_RETRY_DELAYS) - 1)]
                print(f"  [429] Rate limited, waiting {delay}s...")
                time.sleep(delay)
                continue
            resp.raise_for_status()
            data = resp.json()

            # Cache to disk
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            return data

        except requests.RequestException as e:
            delay = SERPAPI_RETRY_DELAYS[min(attempt, len(SERPAPI_RETRY_DELAYS) - 1)]
            print(f"  [Error] {e}, retrying in {delay}s...")
            time.sleep(delay)

    print(f"  [Failed] All {SERPAPI_MAX_RETRIES} attempts failed for params: {cache_params}")
    return None


def batch_search_discovery(
    venues: pd.DataFrame,
    api_key: str,
    output_dir: Path,
    districts: list[str] | None = None,
    search_radius_m: int = 1000,
    max_results_per_query: int = 20,
    log_fn: callable = print,
) -> list[SerpApiSearchResult]:
    """Batch-discover venues with popular_times using SerpApi Search API.

    Strategy (SOP):
      - Use Search queries with category + district area to discover candidates
      - Each search returns up to 20 results — costs 1 API call
      - Match results to local venues by proximity (haversine < 100m)
      - Do NOT call Place API per venue here (that's for validation only)

    Returns list of SerpApiSearchResult with matched local venues.
    """
    if districts is None:
        districts = list(DISTRICT_CENTERS.keys())

    all_results: list[SerpApiSearchResult] = []
    api_calls = 0

    for category_query, google_type, clearpath_type in SERPAPI_SEARCH_CATEGORIES:
        if clearpath_type in OUT_OF_SCOPE_CATEGORIES:
            continue

        for district in districts:
            center = DISTRICT_CENTERS[district]
            location_str = f"{center['lat']},{center['lng']},14"  # lat,lng,zoom

            log_fn(f"  Search: '{category_query}' in {district}...")

            params = {
                "q": f"{category_query} near {district.replace('_', ' ')} Manhattan",
                "ll": f"@{center['lat']},{center['lng']},14z",
                "type": "search",
                "hl": "en",
                "gl": "us",
            }

            data = _serpapi_request(params, api_key, output_dir, cache_prefix="search")
            api_calls += 1

            if not data or "local_results" not in data:
                log_fn(f"    → No results for '{category_query}' in {district}")
                continue

            local_results = data.get("local_results", [])
            log_fn(f"    → {len(local_results)} results returned")

            for result in local_results:
                place_lat = result.get("gps_coordinates", {}).get("latitude")
                place_lng = result.get("gps_coordinates", {}).get("longitude")
                place_id = result.get("place_id", "")
                data_id = result.get("data_id", "")
                name = result.get("title", "")
                address = result.get("address", "")
                rating = result.get("rating")
                reviews = result.get("reviews", 0)
                has_pt = result.get("popular_times") is not None or result.get("busy") is not None

                if place_lat is None or place_lng is None:
                    continue

                # Match to local venues by proximity
                matched_venues = _find_matching_venues(
                    venues, place_lat, place_lng, max_distance_m=100
                )

                serp_result = SerpApiSearchResult(
                    place_id=place_id,
                    data_id=data_id,
                    name=name,
                    address=address,
                    latitude=place_lat,
                    longitude=place_lng,
                    rating=rating,
                    reviews=reviews,
                    type=google_type,
                    has_popular_times=has_pt,
                    popular_times_summary=result.get("popular_times"),
                    search_query=category_query,
                    search_category=clearpath_type,
                    search_district=district,
                )
                all_results.append(serp_result)

            # Respect rate limits
            time.sleep(1)

    log_fn(f"\n  Total Search API calls: {api_calls}")
    log_fn(f"  Total results discovered: {len(all_results)}")
    log_fn(f"  Results with popular_times: {sum(1 for r in all_results if r.has_popular_times)}")

    return all_results


def _find_matching_venues(
    venues: pd.DataFrame,
    lat: float,
    lng: float,
    max_distance_m: float = 100,
) -> pd.DataFrame:
    """Find local venues within max_distance_m of the given coordinates."""
    if len(venues) == 0:
        return pd.DataFrame()

    # Haversine distance calculation
    lat1 = np.radians(venues["latitude"].values)
    lng1 = np.radians(venues["longitude"].values)
    lat2 = np.radians(lat)
    lng2 = np.radians(lng)

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    distances_m = EARTH_RADIUS_M * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    mask = distances_m <= max_distance_m
    result = venues[mask].copy()
    result = result.assign(_distance_m=distances_m[mask])
    return result


# ── Place API validation ───────────────────────────────────────


def validate_candidates_with_place_api(
    candidates: list[SerpApiSearchResult],
    api_key: str,
    output_dir: Path,
    max_calls: int = 100,
    log_fn: callable = print,
) -> list[SerpApiSearchResult]:
    """Validate top candidates using SerpApi Place API.

    Only call Place API for venues that:
    1. Were discovered via Search API
    2. Have a valid place_id
    3. Are among the top candidates (limited by max_calls)

    This is the expensive per-venue call — limited to max_calls.
    """
    # Filter to candidates with valid place_id that haven't been validated yet
    to_validate = [c for c in candidates if c.place_id][:max_calls]

    log_fn(f"  Validating {len(to_validate)} candidates via Place API...")

    validated = []
    api_calls = 0

    for i, candidate in enumerate(to_validate):
        if api_calls >= max_calls:
            log_fn(f"  [Limit] Reached {max_calls} Place API calls, stopping.")
            break

        log_fn(f"  [{i+1}/{len(to_validate)}] Validating: {candidate.name[:40]}...")

        params = {
            "place_id": candidate.place_id,
            "type": "place",
            "hl": "en",
        }

        data = _serpapi_request(params, api_key, output_dir, cache_prefix="place")
        api_calls += 1

        if data and "place_results" in data:
            place = data["place_results"]
            has_pt = place.get("popular_times") is not None
            candidate.has_popular_times = has_pt
            candidate.popular_times_summary = place.get("popular_times")
            candidate.rating = place.get("rating", candidate.rating)
            candidate.reviews = place.get("reviews", candidate.reviews)
            log_fn(f"    → popular_times: {'YES' if has_pt else 'no'}")

        validated.append(candidate)

        # Rate limiting
        time.sleep(0.5)

    log_fn(f"  Place API calls used: {api_calls}")
    return validated


# ── Label status generation ────────────────────────────────────


def generate_label_status(
    venues: pd.DataFrame,
    search_results: list[SerpApiSearchResult],
    citibike_detail: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Generate label status for all venues.

    Assigns label_status, ml_eligible, prediction_source, display_level
    per the SOP:
      - has_popular_times → ml_eligible=True, prediction_source=ml_model
      - no_popular_times → ml_eligible=False, prediction_source=rule_fallback
      - out-of-scope venue_type → ml_eligible=False, prediction_source=none
      - api_not_checked → ml_eligible=False, prediction_source=rule_fallback
    """
    # Build lookup from search results: place_id → has_popular_times
    result_lookup: dict[str, SerpApiSearchResult] = {}
    for r in search_results:
        if r.place_id:
            result_lookup[r.place_id] = r

    # Build venue → matched search result mapping (by proximity + venue_type)
    # Only match venues whose venue_type matches the search result's clearpath category.
    # This prevents false positives (e.g. restroom matched to a nearby hospital search result).
    venue_matches: dict[str, SerpApiSearchResult] = {}
    for r in search_results:
        matched = _find_matching_venues(venues, r.latitude, r.longitude, max_distance_m=100)
        for _, row in matched.iterrows():
            vid = row["venue_id"]
            vtype = row["venue_type"]
            # Skip if venue_type doesn't match the search category
            if vtype != r.search_category:
                continue
            # Keep the best match (has_popular_times = True is better)
            if vid not in venue_matches or (r.has_popular_times and not venue_matches[vid].has_popular_times):
                venue_matches[vid] = r

    # Merge citibike distance
    citibike_map: dict[str, float] = {}
    if citibike_detail is not None:
        for _, row in citibike_detail.iterrows():
            citibike_map[row["venue_id"]] = row.get("citibike_nearest_distance_m", None)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []

    for _, venue in venues.iterrows():
        vid = venue["venue_id"]
        vtype = venue["venue_type"]
        district = venue.get("district", "unknown")
        name = venue.get("name", "")
        lat = venue.get("latitude", 0)
        lng = venue.get("longitude", 0)
        review_count = get_review_count(name)
        rating = venue.get("rating")
        cb_dist = citibike_map.get(vid)

        # Out of scope
        if vtype in OUT_OF_SCOPE_CATEGORIES:
            rows.append(VenueLabelStatus(
                venue_id=vid,
                venue_type=vtype,
                district=district,
                name=name,
                latitude=lat,
                longitude=lng,
                label_status="api_not_checked",
                ml_eligible=False,
                prediction_source="none",
                display_level="no_data",
                serpapi_checked_at=None,
                serpapi_place_id=None,
                priority_score=None,
                category_importance=0,
                review_count=review_count,
                rating=rating,
                citibike_nearest_m=cb_dist,
                notes="AED/emergencyasset: no meaningful busyness data",
            ))
            continue

        # Check if matched via Search API
        match = venue_matches.get(vid)
        if match:
            if match.has_popular_times:
                label_status = "has_popular_times"
                ml_eligible = True
                prediction_source = "ml_model"
                display_level = "quiet"  # will be updated with actual data
            else:
                label_status = "no_popular_times"
                ml_eligible = False
                prediction_source = "rule_fallback"
                display_level = "no_data"

            rows.append(VenueLabelStatus(
                venue_id=vid,
                venue_type=vtype,
                district=district,
                name=name,
                latitude=lat,
                longitude=lng,
                label_status=label_status,
                ml_eligible=ml_eligible,
                prediction_source=prediction_source,
                display_level=display_level,
                serpapi_checked_at=now_str,
                serpapi_place_id=match.place_id,
                priority_score=None,  # calculated separately
                category_importance=CATEGORY_IMPORTANCE.get(vtype, 1),
                review_count=review_count,
                rating=rating,
                citibike_nearest_m=cb_dist,
            ))
        else:
            # Not checked via API
            rows.append(VenueLabelStatus(
                venue_id=vid,
                venue_type=vtype,
                district=district,
                name=name,
                latitude=lat,
                longitude=lng,
                label_status="api_not_checked",
                ml_eligible=False,
                prediction_source="rule_fallback",
                display_level="no_data",
                serpapi_checked_at=None,
                serpapi_place_id=None,
                priority_score=None,
                category_importance=CATEGORY_IMPORTANCE.get(vtype, 1),
                review_count=review_count,
                rating=rating,
                citibike_nearest_m=cb_dist,
                notes="Not discovered via batch Search API",
            ))

    return pd.DataFrame([asdict(r) for r in rows])


# ── Output generators ──────────────────────────────────────────


def generate_candidate_list(
    label_status_df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """Generate ML candidate list: venues eligible for supervised training.

    Filters to ml_eligible=True, sorts by priority_score descending.
    Saves to CSV.
    """
    candidates = label_status_df[label_status_df["ml_eligible"] == True].copy()
    candidates = candidates.sort_values("priority_score", ascending=False)
    candidates.to_csv(output_path, index=False)
    return candidates


def generate_coverage_report(
    category_audit: pd.DataFrame,
    district_audit: pd.DataFrame,
    citibike_audit: pd.DataFrame,
    label_status_df: pd.DataFrame,
    search_results: list[SerpApiSearchResult],
    output_path: Path,
) -> str:
    """Generate markdown coverage audit report.

    Returns the report as a string and saves to output_path.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(label_status_df)
    in_scope_df = label_status_df[~label_status_df["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES)]
    out_scope_df = label_status_df[label_status_df["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES)]
    in_scope = len(in_scope_df)
    out_scope = len(out_scope_df)
    has_pt = len(in_scope_df[in_scope_df["label_status"] == "has_popular_times"])
    no_pt = len(in_scope_df[in_scope_df["label_status"] == "no_popular_times"])
    not_checked = len(in_scope_df[in_scope_df["label_status"] == "api_not_checked"])

    report = f"""# Venue ML Coverage Audit Report

> Generated: {now}

## Summary

| Metric | Count | Pct |
|--------|------:|----:|
| Total venues | {total} | 100% |
| In-scope (healthcare + restroom) | {in_scope} | {in_scope/total*100:.1f}% |
| Out-of-scope (AED) | {out_scope} | {out_scope/total*100:.1f}% |
| Has popular_times | {has_pt} | {has_pt/in_scope*100:.1f}% of in-scope |
| No popular_times | {no_pt} | {no_pt/in_scope*100:.1f}% of in-scope |
| Not checked (API) | {not_checked} | {not_checked/in_scope*100:.1f}% of in-scope |
| **ML eligible** | **{has_pt}** | **{has_pt/in_scope*100:.1f}% of in-scope** |

## SerpApi Usage

- Search API calls: {len(set(r.search_query + r.search_district for r in search_results))} category×district queries
- Results discovered: {len(search_results)}
- Results with popular_times: {sum(1 for r in search_results if r.has_popular_times)}

## Category Coverage

{category_audit.to_markdown(index=False)}

## District Coverage

{district_audit.to_markdown(index=False)}

## Citi Bike Proximity Distribution

{citibike_audit.to_markdown(index=False) if len(citibike_audit) > 0 else "No Citi Bike data available."}

## Label Status Distribution

| Label Status | Count | Pct of Total | Pct of In-Scope |
|-------------|------:|----:|----:|
"""
    for status, group in in_scope_df.groupby("label_status"):
        cnt = len(group)
        pct_total = cnt / total * 100
        pct_scope = cnt / in_scope * 100 if in_scope > 0 else 0
        report += f"| {status} | {cnt} | {pct_total:.1f}% | {pct_scope:.1f}% |\n"

    if out_scope:
        report += f"\nOut-of-scope venues are tracked by `venue_type`, not `label_status`: {out_scope} venues ({out_scope/total*100:.1f}% of total).\n"

    report += f"""
## SOP Compliance

- ✅ Search queries used for batch discovery (not per-venue Place API calls)
- ✅ Place API only for final label validation
- ✅ Raw response caching implemented at `serpapi_raw_responses/` for live SerpApi runs
- ✅ Each venue has explicit `label_status` and `ml_eligible`
- ✅ Out-of-scope venues (AED/emergencyasset) excluded from ML training
- ✅ Coverage audit includes category, district, and Citi Bike proximity dimensions
- ✅ `prediction_source` distinguishes `ml_model` from `rule_fallback`

## Non-Range

- AED/emergencyasset venues: out of scope for supervised ML (no meaningful busyness)
- Restrooms: sparse Google Popular Times coverage; rule_fallback recommended
- Historical time series: not covered by SerpApi (requires BestTime or custom ETL)
"""

    output_path.write_text(report)
    return report


def save_run_metadata(
    venues: pd.DataFrame,
    search_results: list[SerpApiSearchResult],
    label_status_df: pd.DataFrame,
    output_dir: Path,
    api_calls_search: int,
    api_calls_place: int,
) -> dict:
    """Save run metadata as JSON for reproducibility."""
    meta = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "venue_input": {
            "total_rows": len(venues),
            "venue_types": venues["venue_type"].value_counts().to_dict(),
            "districts": venues["district"].value_counts().to_dict(),
        },
        "serpapi_usage": {
            "search_calls": api_calls_search,
            "place_calls": api_calls_place,
            "total_calls": api_calls_search + api_calls_place,
            "monthly_quota_remaining": 250 - api_calls_search - api_calls_place,
        },
        "results": {
            "total_discovered": len(search_results),
            "with_popular_times": sum(1 for r in search_results if r.has_popular_times),
        },
        "label_status": label_status_df["label_status"].value_counts().to_dict(),
        "out_of_scope_count": int(label_status_df["venue_type"].isin(OUT_OF_SCOPE_CATEGORIES).sum()),
        "ml_eligible_count": int(label_status_df["ml_eligible"].sum()),
    }

    meta_path = output_dir / "run_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta

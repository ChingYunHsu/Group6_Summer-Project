"""venue_coverage.py — Spatial coverage test for project venues.

Measures how many venues have at least one usable data-source point within
configurable GPS radii (100m–500m). Sources: Citi Bike GBFS, MTA Subway,
NYC Traffic.

Data flow:
  Load venues_clean.csv → Deduplicate by venue_id
  → Fetch source points (Citi Bike / MTA / Traffic)
  → Build BallTree per source → Query nearest distance per venue
  → Aggregate coverage by radius, venue_type, district
  → Generate CSV + JSON + Markdown + PNG artifacts

Usage:
  cd Data+ML/test/6.8-6.12_DB
  python -m dqr.venue_coverage --help  (not the CLI entry — see run_venue_coverage.py)
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from sklearn.neighbors import BallTree

# ── Constants ──────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_008.8  # mean Earth radius in metres

CITIBIKE_INFO_URL = (
    "https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_information.json"
)
CITIBIKE_STATUS_URL = (
    "https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_status.json"
)

MTA_DATASET_ID = "5f5g-n3cz"
MTA_SODA_URL = f"https://data.ny.gov/resource/{MTA_DATASET_ID}.json"

TRAFFIC_DATASET_ID = "7ym2-wayt"
TRAFFIC_SODA_URL = (
    f"https://data.cityofnewyork.us/resource/{TRAFFIC_DATASET_ID}.json"
)

SUPPORTED_SOURCES = ("citibike", "mta", "traffic")

# Prediction scope — AED/emergencyasset excluded from busyness prediction
PREDICTION_SCOPE_MAP = {
    "emergencyasset": {
        "prediction_scope": False,
        "scope_reason": "no_meaningful_busyness_target",
    },
    "healthcare": {
        "prediction_scope": True,
        "scope_reason": "visit_based_venue",
    },
    "restroom": {
        "prediction_scope": True,
        "scope_reason": "visit_based_venue",
    },
}

DEFAULT_TIMEOUT = (2, 5)  # (connect, read) seconds — SOP §7.2
DEFAULT_MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds between retries
MAX_POINTS_PER_SOURCE = 20_000
DEFAULT_PAGE_SIZE = 5_000


# ── Data classes ───────────────────────────────────────────────


@dataclass
class SourcePoint:
    """Standardised spatial point from one data source."""
    source: str
    source_id: str
    name: str
    latitude: float
    longitude: float
    source_timestamp: str | None = None


@dataclass
class SourceResult:
    """Outcome of fetching and normalising one source."""
    source: str
    status: str = "ok"  # "ok" or "failed"
    points: list[SourcePoint] = field(default_factory=list)
    raw_count: int = 0
    valid_count: int = 0
    unique_id_count: int = 0
    unique_coord_count: int = 0
    rejected_count: int = 0
    fetch_time_s: float = 0.0
    max_source_timestamp: str | None = None
    api_url: str = ""
    dataset_id: str = ""
    query_text: str = ""
    retry_count: int = 0
    error_type: str = ""
    error_message: str = ""
    year_profile: list[dict] | None = None  # Traffic year distribution


@dataclass
class CoverageRow:
    """Per-venue nearest-distance result for one source."""
    venue_id: str
    nearest_source_id: str
    nearest_distance_m: float


# ── HTTP Client ────────────────────────────────────────────────


def _request_with_retries(
    url: str,
    params: dict | None = None,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> tuple[requests.Response, int]:
    """GET with retry on transient failures.

    Retries: connection errors, HTTP 429, HTTP 5xx.
    Does NOT retry: read timeouts (fail immediately), other HTTP 4xx.

    Returns:
        (response, retry_count) where retry_count is the number of retries
        actually performed (0 if first attempt succeeded).
    """
    last_exc: Exception | None = None
    retries = 0
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries:
                    retries += 1
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                    continue
            resp.raise_for_status()
            return resp, retries
        except requests.Timeout:
            # Timeout → fail immediately, no retry
            raise
        except requests.ConnectionError as exc:
            last_exc = exc
            if attempt < max_retries:
                retries += 1
                time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                continue
            raise
        except requests.HTTPError:
            raise
    # Should not reach here, but satisfy type checker
    raise last_exc  # type: ignore[misc]


def fetch_json(
    url: str,
    params: dict | None = None,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> tuple[Any, int]:
    """Fetch JSON from *url* with retries. Returns (parsed_json, retry_count)."""
    resp, retries = _request_with_retries(url, params=params, timeout=timeout,
                                          max_retries=max_retries)
    return resp.json(), retries


def fetch_soda_pages(
    url: str,
    params: dict,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    max_points: int = MAX_POINTS_PER_SOURCE,
) -> tuple[list[dict], int]:
    """Paginate a SODA endpoint using $limit/$offset.

    Stops when a page returns fewer than *page_size* rows.
    Raises ValueError if *max_points* rows are exceeded.

    Returns:
        (all_rows, total_retries)
    """
    all_rows: list[dict] = []
    offset = 0
    total_retries = 0
    while True:
        p = dict(params)
        p["$limit"] = page_size
        p["$offset"] = offset
        resp, retries = _request_with_retries(url, params=p, timeout=timeout,
                                              max_retries=max_retries)
        total_retries += retries
        rows = resp.json()
        all_rows.extend(rows)
        # Check safety limit immediately after extending — before the
        # short-page break so the last short page cannot sneak past.
        if len(all_rows) > max_points:
            raise ValueError(
                f"Source exceeded {max_points} rows ({len(all_rows)} fetched) — aborting"
            )
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows, total_retries


# ── Source Adapters ────────────────────────────────────────────


def _normalise_points(
    raw_points: list[SourcePoint],
) -> tuple[list[SourcePoint], int, int, int, int, int]:
    """Deduplicate and validate a list of SourcePoints.

    Returns:
        (deduped_points, raw_count, valid_count, unique_id_count,
         unique_coord_count, rejected_count)
    """
    raw_count = len(raw_points)

    # Step 1: Remove records with missing / non-numeric coords
    valid: list[SourcePoint] = []
    rejected = 0
    for pt in raw_points:
        if pt.latitude is None or pt.longitude is None:
            rejected += 1
            continue
        if not isinstance(pt.latitude, (int, float)) or not isinstance(
            pt.longitude, (int, float)
        ):
            rejected += 1
            continue
        if math.isnan(pt.latitude) or math.isnan(pt.longitude):
            rejected += 1
            continue
        if not (-90 <= pt.latitude <= 90) or not (-180 <= pt.longitude <= 180):
            rejected += 1
            continue
        valid.append(pt)

    valid_count = len(valid)

    # Step 2: Deduplicate by source_id, keep first
    seen_ids: set[str] = set()
    by_id: list[SourcePoint] = []
    for pt in valid:
        if pt.source_id not in seen_ids:
            seen_ids.add(pt.source_id)
            by_id.append(pt)
    unique_id_count = len(by_id)

    # Step 3: Deduplicate coordinates for spatial calc
    seen_coords: set[tuple[float, float]] = set()
    deduped: list[SourcePoint] = []
    for pt in by_id:
        coord = (round(pt.latitude, 8), round(pt.longitude, 8))
        if coord not in seen_coords:
            seen_coords.add(coord)
            deduped.append(pt)
    unique_coord_count = len(deduped)

    return deduped, raw_count, valid_count, unique_id_count, unique_coord_count, rejected


def fetch_citibike(
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> SourceResult:
    """Fetch Citi Bike stations from GBFS."""
    result = SourceResult(source="citibike")
    t0 = time.monotonic()
    try:
        info_data, retries_info = fetch_json(CITIBIKE_INFO_URL, timeout=timeout,
                                             max_retries=max_retries)
        result.retry_count += retries_info
        result.api_url = CITIBIKE_INFO_URL

        info_stations = info_data.get("data", {}).get("stations", [])
        info_last_updated = info_data.get("last_updated")
        info_ttl = info_data.get("ttl")

        # Track total API rows for accurate raw_count
        api_row_count = len(info_stations)
        adapter_skipped = 0

        # Optionally join with status for installed/operational filter
        try:
            status_data, retries_status = fetch_json(
                CITIBIKE_STATUS_URL, timeout=timeout, max_retries=max_retries)
            result.retry_count += retries_status
            status_stations = status_data.get("data", {}).get("stations", [])
            status_map = {
                s["station_id"]: s for s in status_stations
            }
        except Exception:
            status_map = {}

        raw_points: list[SourcePoint] = []
        for st in info_stations:
            sid = str(st.get("station_id", ""))
            name = st.get("name", "")
            lat = st.get("lat")
            lon = st.get("lon")
            if lat is None or lon is None:
                adapter_skipped += 1
                continue
            # If status available, filter to installed+operational
            if status_map:
                status = status_map.get(sid, {})
                if not status.get("is_installed", True):
                    adapter_skipped += 1
                    continue
                if not status.get("is_renting", True):
                    adapter_skipped += 1
                    continue
            raw_points.append(SourcePoint(
                source="citibike",
                source_id=sid,
                name=name,
                latitude=float(lat),
                longitude=float(lon),
                source_timestamp=(
                    datetime.fromtimestamp(info_last_updated, tz=timezone.utc).isoformat()
                    if info_last_updated else None
                ),
            ))

        result.max_source_timestamp = (
            datetime.fromtimestamp(info_last_updated, tz=timezone.utc).isoformat()
            if info_last_updated else None
        )
        result.dataset_id = "gbfs_lyft_bkn"
        result.query_text = f"station_information + station_status, ttl={info_ttl}"

        deduped, raw, valid, uid, ucoord, rej = _normalise_points(raw_points)
        result.points = deduped
        # raw_count = total API rows (before any adapter filtering)
        result.raw_count = api_row_count
        result.valid_count = valid
        result.unique_id_count = uid
        result.unique_coord_count = ucoord
        # rejected = adapter skips + normalise rejects
        result.rejected_count = adapter_skipped + rej

    except Exception as exc:
        result.status = "failed"
        result.error_type = type(exc).__name__
        result.error_message = str(exc)[:200]
    result.fetch_time_s = time.monotonic() - t0
    return result


def fetch_mta(
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> SourceResult:
    """Fetch MTA station complexes from the official station complex dataset.

    Uses dataset 5f5g-n3cz which directly contains station_complex_id,
    display_name, latitude, and longitude — no OD aggregation needed.
    """
    result = SourceResult(source="mta")
    t0 = time.monotonic()
    try:
        result.api_url = MTA_SODA_URL
        result.dataset_id = MTA_DATASET_ID

        # Direct query — no GROUP BY needed; dataset has one row per complex
        params = {
            "$select": "complex_id, display_name, latitude, longitude",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
            "$order": "complex_id",
            "$limit": page_size,
            "$offset": 0,
        }
        result.query_text = (
            f"SELECT complex_id, display_name, lat/lng from {MTA_DATASET_ID}"
        )

        rows, retries = fetch_soda_pages(
            MTA_SODA_URL, params, page_size=page_size,
            timeout=timeout, max_retries=max_retries,
        )
        result.retry_count += retries

        # Track API row count before adapter filtering
        api_row_count = len(rows)
        adapter_skipped = 0

        raw_points: list[SourcePoint] = []
        for r in rows:
            sid = str(r.get("complex_id", ""))
            name = r.get("display_name", "")
            lat = r.get("latitude")
            lon = r.get("longitude")
            if lat is None or lon is None:
                adapter_skipped += 1
                continue
            raw_points.append(SourcePoint(
                source="mta",
                source_id=sid,
                name=name,
                latitude=float(lat),
                longitude=float(lon),
            ))

        result.max_source_timestamp = "timestamp_unavailable"

        deduped, raw, valid, uid, ucoord, rej = _normalise_points(raw_points)
        result.points = deduped
        result.raw_count = api_row_count
        result.valid_count = valid
        result.unique_id_count = uid
        result.unique_coord_count = ucoord
        result.rejected_count = adapter_skipped + rej

    except Exception as exc:
        result.status = "failed"
        result.error_type = type(exc).__name__
        result.error_message = str(exc)[:200]
    result.fetch_time_s = time.monotonic() - t0
    return result


def fetch_traffic(
    year: int = 2025,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> SourceResult:
    """Fetch NYC Traffic segments with coordinate transformation."""
    result = SourceResult(source="traffic")
    t0 = time.monotonic()

    # Cache the transformer at module level
    global _traffic_transformer
    if "_traffic_transformer" not in globals():
        _traffic_transformer = None

    try:
        result.api_url = TRAFFIC_SODA_URL
        result.dataset_id = TRAFFIC_DATASET_ID

        # Server-side grouping: one geometry per segment
        params = {
            "$select": "segmentid, street, wktgeom, count(*) as n_records",
            "$where": f"yr='{year}' AND boro='Manhattan'",
            "$group": "segmentid, street, wktgeom",
            "$order": "segmentid",
            "$limit": page_size,
            "$offset": 0,
        }
        result.query_text = (
            f"SoQL group by segmentid for year {year}, boro=Manhattan"
        )

        rows, retries = fetch_soda_pages(
            TRAFFIC_SODA_URL, params, page_size=page_size,
            timeout=timeout, max_retries=max_retries,
        )
        result.retry_count += retries

        # Track API row count before adapter filtering
        api_row_count = len(rows)

        # Parse WKT and convert EPSG:2263 → WGS84
        import re
        _wkt_re = re.compile(r"POINT\s*\(([\d.]+)\s+([\d.]+)\)")

        if _traffic_transformer is None:
            try:
                from pyproj import Transformer
                _traffic_transformer = Transformer.from_crs(
                    "EPSG:2263", "EPSG:4326", always_xy=True
                )
            except ImportError:
                _traffic_transformer = None

        raw_points: list[SourcePoint] = []
        coord_failures = 0
        for r in rows:
            sid = str(r.get("segmentid", ""))
            name = r.get("street", "")
            wkt = r.get("wktgeom", "")
            m = _wkt_re.match(wkt)
            if not m:
                coord_failures += 1
                continue
            x, y = float(m.group(1)), float(m.group(2))
            if _traffic_transformer is not None:
                lng, lat = _traffic_transformer.transform(x, y)
            else:
                # No pyproj — cannot transform coordinates
                coord_failures += 1
                continue
            raw_points.append(SourcePoint(
                source="traffic",
                source_id=sid,
                name=name,
                latitude=lat,
                longitude=lng,
            ))

        result.max_source_timestamp = "timestamp_unavailable"

        # Year distribution diagnostic — separate query, non-fatal on failure
        try:
            year_params = {
                "$select": "yr, count(*) as record_count, count(segmentid) as unique_segment_count",
                "$where": "boro='Manhattan'",
                "$group": "yr",
                "$order": "yr",
            }
            year_rows, _ = fetch_soda_pages(
                TRAFFIC_SODA_URL, year_params, page_size=100,
                timeout=timeout, max_retries=1,
            )
            result.year_profile = [
                {
                    "year": r.get("yr", ""),
                    "record_count": int(r.get("record_count", 0)),
                    "unique_segment_count": int(r.get("unique_segment_count", 0)),
                }
                for r in year_rows
            ]
        except Exception:
            result.year_profile = None

        deduped, raw, valid, uid, ucoord, rej = _normalise_points(raw_points)
        result.points = deduped
        # raw_count = total API rows (before any adapter filtering)
        result.raw_count = api_row_count
        result.valid_count = valid
        result.unique_id_count = uid
        result.unique_coord_count = ucoord
        # rejected = coord failures (adapter) + normalise rejects
        result.rejected_count = coord_failures + rej

    except Exception as exc:
        result.status = "failed"
        result.error_type = type(exc).__name__
        result.error_message = str(exc)[:200]
    result.fetch_time_s = time.monotonic() - t0
    return result


# ── Venue Loading ──────────────────────────────────────────────


def load_venues(venue_file: str | Path) -> tuple[pd.DataFrame, int]:
    """Load and deduplicate venues by venue_id.

    Returns:
        (deduped_df, duplicate_venue_id_count)
    """
    df = pd.read_csv(venue_file)
    total_before = len(df)
    df = df.drop_duplicates(subset=["venue_id"], keep="first")
    dup_count = total_before - len(df)
    return df, dup_count


def add_prediction_scope(venues_df: pd.DataFrame) -> pd.DataFrame:
    """Add prediction_scope and scope_reason columns based on venue_type.

    prediction_scope=True  → healthcare, restroom (visit-based, busyness meaningful)
    prediction_scope=False → emergencyasset / AED (no busyness target)
    """
    df = venues_df.copy()
    df["prediction_scope"] = df["venue_type"].map(
        lambda vt: PREDICTION_SCOPE_MAP.get(vt, {}).get("prediction_scope", True)
    )
    df["scope_reason"] = df["venue_type"].map(
        lambda vt: PREDICTION_SCOPE_MAP.get(vt, {}).get("scope_reason", "visit_based_venue")
    )
    return df


def compute_aed_summary(
    detail_df: pd.DataFrame,
    radii: list[int],
) -> pd.DataFrame:
    """Compute AED/emergencyasset asset-status coverage summary.

    Returns DataFrame with same schema as compute_standalone_coverage,
    but scope='aed_summary' and only emergencyasset venues.
    """
    aed_df = detail_df[detail_df["venue_type"] == "emergencyasset"].copy()
    if aed_df.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for src in ["citibike", "mta", "traffic"]:
        dist_col = f"{src}_nearest_distance_m"
        if dist_col not in aed_df.columns:
            continue
        distances = aed_df[dist_col].values
        venue_count = len(aed_df)
        prev_covered = 0
        for radius in radii:
            covered = int((distances <= radius).sum())
            rate = covered / venue_count
            marginal = covered - prev_covered
            marginal_pp = rate - (prev_covered / venue_count)
            rows.append({
                "scope": "aed_summary",
                "group_name": "venue_type",
                "group_value": "emergencyasset",
                "coverage_kind": "standalone",
                "source_or_combination": src,
                "radius_m": radius,
                "venue_count": venue_count,
                "covered_count": covered,
                "coverage_rate": round(rate, 6),
                "incremental_covered_count": marginal,
                "marginal_gain_pp": round(marginal_pp, 6),
                "nearest_distance_median": round(float(np.median(distances)), 2),
                "nearest_distance_p90": round(float(np.percentile(distances, 90)), 2),
            })
            prev_covered = covered
    return pd.DataFrame(rows)


# ── Spatial Algorithm ──────────────────────────────────────────


def compute_nearest_distances(
    venue_lats: np.ndarray,
    venue_lons: np.ndarray,
    source_lats: np.ndarray,
    source_lons: np.ndarray,
    source_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a BallTree from source coords and query nearest for each venue.

    Args:
        venue_lats, venue_lons: venue coordinates in degrees
        source_lats, source_lons: source point coordinates in degrees
        source_ids: source identifier array

    Returns:
        (nearest_distances_m, nearest_source_ids) arrays aligned with venues
    """
    if len(source_lats) == 0:
        n = len(venue_lats)
        return np.full(n, np.inf), np.full(n, "", dtype=object)

    # Convert to radians
    venue_rad = np.radians(np.column_stack([venue_lats, venue_lons]))
    source_rad = np.radians(np.column_stack([source_lats, source_lons]))

    tree = BallTree(source_rad, metric="haversine")
    dist_rad, idx = tree.query(venue_rad, k=1)

    # Convert angular distance to metres
    dist_m = dist_rad.flatten() * EARTH_RADIUS_M
    nearest_ids = source_ids[idx.flatten()]

    return dist_m, nearest_ids


def compute_radius_flags(
    distances_m: np.ndarray, radii: list[int]
) -> dict[int, np.ndarray]:
    """For a 1-D array of nearest distances, produce a boolean flag per radius."""
    return {r: (distances_m <= r) for r in radii}


# ── Coverage Aggregation ──────────────────────────────────────


def compute_standalone_coverage(
    detail_df: pd.DataFrame,
    source: str,
    radii: list[int],
) -> pd.DataFrame:
    """Compute standalone coverage metrics for one source across all radii.

    Returns DataFrame with columns:
        scope, group_name, group_value, coverage_kind,
        source_or_combination, radius_m, venue_count, covered_count,
        coverage_rate, incremental_covered_count, marginal_gain_pp,
        nearest_distance_median, nearest_distance_p90
    """
    dist_col = f"{source}_nearest_distance_m"
    rows: list[dict] = []

    for scope, group_col in [("overall", None), ("venue_type", "venue_type"),
                              ("district", "district")]:
        if scope == "overall":
            groups = [("_all", detail_df)]
        else:
            groups = [(g, sub) for g, sub in detail_df.groupby(group_col, dropna=False)]

        for group_value, grp in groups:
            # Skip NaN/empty group values
            if group_col and (pd.isna(group_value) or str(group_value).strip() == ""):
                continue
            distances = grp[dist_col].values
            venue_count = len(grp)
            if venue_count == 0:
                continue
            prev_covered = 0
            for radius in radii:
                covered = int((distances <= radius).sum())
                rate = covered / venue_count
                marginal = covered - prev_covered
                marginal_pp = rate - (prev_covered / venue_count)
                rows.append({
                    "scope": scope,
                    "group_name": group_col or "overall",
                    "group_value": group_value,
                    "coverage_kind": "standalone",
                    "source_or_combination": source,
                    "radius_m": radius,
                    "venue_count": venue_count,
                    "covered_count": covered,
                    "coverage_rate": round(rate, 6),
                    "incremental_covered_count": marginal,
                    "marginal_gain_pp": round(marginal_pp, 6),
                    "nearest_distance_median": round(float(np.median(distances)), 2),
                    "nearest_distance_p90": round(float(np.percentile(distances, 90)), 2),
                })
                prev_covered = covered

    return pd.DataFrame(rows)


def compute_cumulative_coverage(
    detail_df: pd.DataFrame,
    sources: list[str],
    radii: list[int],
    successful_sources: set[str] | None = None,
) -> pd.DataFrame:
    """Compute cumulative (combination) coverage in fixed source order.

    Combinations follow the SOP-defined fixed prefix order:
        C1 = sources[0]
        C2 = sources[0] + sources[1]
        C3 = sources[0] + sources[1] + sources[2]

    A combination is emitted only if every source in its prefix succeeded.
    Once a failed source is encountered, no further (longer) combinations
    are produced — the failed source is NOT skipped over. (SOP §7.3 / §10.2)

    Args:
        sources: the full requested source order (e.g. citibike, mta, traffic).
        radii: radii in metres.
        successful_sources: set of source names that fetched successfully.
            Defaults to all of *sources* (back-compat for standalone callers).
    """
    if successful_sources is None:
        successful_sources = set(sources)

    # Build the list of valid cumulative prefixes: a prefix is valid only if
    # every source in it succeeded; we stop at the first failure.
    valid_prefixes: list[list[str]] = []
    for i, src in enumerate(sources):
        if src not in successful_sources:
            break  # first failure — no longer combinations
        valid_prefixes.append(sources[: i + 1])

    rows: list[dict] = []

    for scope, group_col in [("overall", None), ("venue_type", "venue_type"),
                              ("district", "district")]:
        if scope == "overall":
            groups = [("_all", detail_df)]
        else:
            groups = [(g, sub) for g, sub in detail_df.groupby(group_col, dropna=False)]

        for group_value, grp in groups:
            # Skip NaN/empty group values
            if group_col and (pd.isna(group_value) or str(group_value).strip() == ""):
                continue
            venue_count = len(grp)
            if venue_count == 0:
                continue
            for radius in radii:
                cumulative_covered: set[int] = set()
                for prefix in valid_prefixes:
                    new_src = prefix[-1]
                    dist_col = f"{new_src}_nearest_distance_m"
                    if dist_col not in grp.columns:
                        continue
                    dists = grp[dist_col].values
                    covered_idx = set(np.where(dists <= radius)[0])
                    prev_count = len(cumulative_covered)
                    cumulative_covered |= covered_idx
                    new_count = len(cumulative_covered)
                    combo_label = " + ".join(prefix)
                    rows.append({
                        "scope": scope,
                        "group_name": group_col or "overall",
                        "group_value": group_value,
                        "coverage_kind": "cumulative",
                        "source_or_combination": combo_label,
                        "radius_m": radius,
                        "venue_count": venue_count,
                        "covered_count": new_count,
                        "coverage_rate": round(new_count / venue_count, 6),
                        "incremental_covered_count": new_count - prev_count,
                        "marginal_gain_pp": round(
                            (new_count - prev_count) / venue_count, 6
                        ),
                        "nearest_distance_median": None,
                        "nearest_distance_p90": None,
                    })

    return pd.DataFrame(rows)


# ── Artifact Generation ───────────────────────────────────────


def generate_markdown_report(
    metadata: dict,
    summary_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    source_results: dict[str, SourceResult],
    radii: list[int],
) -> str:
    """Generate the coverage_report.md content."""
    lines: list[str] = []
    lines.append("# Venue Spatial Coverage Report\n")
    lines.append(f"**Run ID:** {metadata['run_id']}  ")
    lines.append(f"**Generated:** {metadata['completed_at']}  ")
    lines.append(f"**Venue count:** {metadata['venue_input']['unique_venue_count']}  ")
    lines.append(f"**Radii:** {', '.join(str(r) + 'm' for r in radii)}\n")

    # Section 1: Run summary
    lines.append("## 1. Run Summary\n")
    lines.append(f"- Started: {metadata['started_at']}")
    lines.append(f"- Completed: {metadata['completed_at']}")
    lines.append(f"- Venue file: `{metadata['venue_input']['file_path']}`")
    lines.append(f"- Total rows: {metadata['venue_input']['total_rows']}")
    lines.append(f"- Duplicate venue_id removed: {metadata['venue_input']['duplicate_venue_id_count']}")
    lines.append(f"- Unique venues: {metadata['venue_input']['unique_venue_count']}\n")

    # Section 2: Source status
    lines.append("## 2. Source Status and Freshness\n")
    lines.append("| Source | Status | Fetch Time | Raw | Valid | Unique IDs | Unique Coords | Rejected | Timestamp |")
    lines.append("|--------|--------|------------|-----|-------|------------|---------------|----------|-----------|")
    for src_name, sr in source_results.items():
        lines.append(
            f"| {src_name} | {sr.status} | {sr.fetch_time_s:.1f}s | "
            f"{sr.raw_count} | {sr.valid_count} | {sr.unique_id_count} | "
            f"{sr.unique_coord_count} | {sr.rejected_count} | "
            f"{sr.max_source_timestamp or 'N/A'} |"
        )
    lines.append("")

    # Section 3: Overall standalone coverage
    lines.append("## 3. Overall Standalone Coverage\n")
    standalone = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "standalone")
    ]
    if not standalone.empty:
        lines.append("| Source | Radius | Venue Count | Covered | Coverage Rate | Marginal (pp) |")
        lines.append("|--------|--------|-------------|---------|---------------|---------------|")
        for _, row in standalone.iterrows():
            lines.append(
                f"| {row['source_or_combination']} | {row['radius_m']}m | "
                f"{row['venue_count']} | {row['covered_count']} | "
                f"{row['coverage_rate']:.1%} | +{row['marginal_gain_pp']:.1%} |"
            )
    lines.append("")

    # Section 4: Cumulative coverage
    lines.append("## 4. Cumulative Coverage and Source Marginal Contribution\n")
    cumulative = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "cumulative")
    ]
    if not cumulative.empty:
        lines.append("| Combination | Radius | Cumulative Covered | Cumulative Rate | Incremental | Gain (pp) |")
        lines.append("|-------------|--------|--------------------|-----------------|-------------|-----------|")
        for _, row in cumulative.iterrows():
            lines.append(
                f"| {row['source_or_combination']} | {row['radius_m']}m | "
                f"{row['covered_count']} | {row['coverage_rate']:.1%} | "
                f"+{row['incremental_covered_count']} | +{row['marginal_gain_pp']:.1%} |"
            )
    lines.append("")

    # Section 5: Coverage by venue_type
    lines.append("## 5. Coverage by Venue Type\n")
    vt_data = summary_df[
        (summary_df["scope"] == "venue_type")
        & (summary_df["coverage_kind"] == "standalone")
    ]
    if not vt_data.empty:
        for vt in vt_data["group_value"].unique():
            sub = vt_data[vt_data["group_value"] == vt]
            lines.append(f"### {vt}\n")
            lines.append("| Source | Radius | Covered | Rate |")
            lines.append("|--------|--------|---------|------|")
            for _, row in sub.iterrows():
                lines.append(
                    f"| {row['source_or_combination']} | {row['radius_m']}m | "
                    f"{row['covered_count']}/{row['venue_count']} | "
                    f"{row['coverage_rate']:.1%} |"
                )
            lines.append("")

    # Section 6: Coverage by district
    lines.append("## 6. Coverage by District\n")
    dist_data = summary_df[
        (summary_df["scope"] == "district")
        & (summary_df["coverage_kind"] == "standalone")
    ]
    if not dist_data.empty:
        for d in dist_data["group_value"].unique():
            sub = dist_data[dist_data["group_value"] == d]
            lines.append(f"### {d}\n")
            lines.append("| Source | Radius | Covered | Rate |")
            lines.append("|--------|--------|---------|------|")
            for _, row in sub.iterrows():
                lines.append(
                    f"| {row['source_or_combination']} | {row['radius_m']}m | "
                    f"{row['covered_count']}/{row['venue_count']} | "
                    f"{row['coverage_rate']:.1%} |"
                )
            lines.append("")

    # Section 7: Distance distribution
    lines.append("## 7. Nearest-Distance Distribution\n")
    dist_rows = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "standalone")
    ].drop_duplicates(subset=["source_or_combination"])
    if not dist_rows.empty:
        lines.append("| Source | Median (m) | P90 (m) |")
        lines.append("|--------|------------|---------|")
        for _, row in dist_rows.iterrows():
            med = row.get("nearest_distance_median", "N/A")
            p90 = row.get("nearest_distance_p90", "N/A")
            lines.append(
                f"| {row['source_or_combination']} | {med} | {p90} |"
            )
    lines.append("")

    # Section 8: Uncovered venue counts
    lines.append("## 8. Uncovered Venue Counts\n")
    if not standalone.empty:
        last_radius = radii[-1]
        for src in standalone["source_or_combination"].unique():
            row = standalone[
                (standalone["source_or_combination"] == src)
                & (standalone["radius_m"] == last_radius)
            ]
            if not row.empty:
                uncovered = row.iloc[0]["venue_count"] - row.iloc[0]["covered_count"]
                lines.append(f"- **{src}** at {last_radius}m: {uncovered} uncovered venues")
    lines.append("")

    # Section 9: Data-quality warnings
    lines.append("## 9. Data-Quality Warnings\n")
    for src_name, sr in source_results.items():
        if sr.status == "failed":
            lines.append(f"- **{src_name}**: FAILED — {sr.error_type}: {sr.error_message}")
        elif sr.rejected_count > 0:
            lines.append(f"- **{src_name}**: {sr.rejected_count} rejected records")
    if not any(sr.status == "failed" for sr in source_results.values()):
        lines.append("- No critical warnings.\n")

    # Section 10: Data applicability warning
    lines.append("## 10. Data Applicability Warning\n")
    lines.append("- NYC Traffic segments represent road-level sensor coverage, not pedestrian volume.")
    lines.append("- Low segment count for the requested year reflects official data sparsity,")
    lines.append("  not a parsing error.")
    lines.append("- Spatial coverage does NOT imply the source captures venue-level activity.\n")

    # Section 11: Traffic year profile (if available)
    traffic_sr = source_results.get("traffic")
    if traffic_sr and traffic_sr.year_profile:
        lines.append("## 11. Traffic Year Profile\n")
        lines.append("| Year | Record Count | Unique Segments |")
        lines.append("|------|-------------|-----------------|")
        for yp in traffic_sr.year_profile:
            lines.append(
                f"| {yp['year']} | {yp['record_count']} | {yp['unique_segment_count']} |"
            )
        lines.append("")

    # Section 12: Interpretation constraints
    lines.append("## 12. Interpretation Constraints\n")
    lines.append("- Spatial coverage does NOT indicate prediction quality or pedestrian busyness.")
    lines.append("- NYC Traffic segments are road-level, not venue-level; coverage ≠ correlation.")
    lines.append("- No production radius is recommended; review marginal results per 100m increment.")
    lines.append("- BestTime is excluded (paid venue-level source).")
    lines.append("- Pedestrian sensors are excluded from primary coverage (sparse active coverage).\n")

    return "\n".join(lines)


def generate_charts(
    output_dir: Path,
    summary_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    source_results: dict[str, SourceResult],
    radii: list[int],
    run_id: str,
) -> list[str]:
    """Generate four PNG charts. Returns list of filenames created."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    filenames: list[str] = []
    timestamp_label = f"Run: {run_id}"

    # 1. coverage_by_radius.png
    fig, ax = plt.subplots(figsize=(10.67, 6))  # 1600x900 @ 150 DPI
    overall_standalone = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "standalone")
    ]
    for src in overall_standalone["source_or_combination"].unique():
        sub = overall_standalone[overall_standalone["source_or_combination"] == src]
        ax.plot(sub["radius_m"], sub["coverage_rate"], marker="o", label=src)

    overall_cumulative = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "cumulative")
    ]
    for combo in overall_cumulative["source_or_combination"].unique():
        sub = overall_cumulative[overall_cumulative["source_or_combination"] == combo]
        ax.plot(sub["radius_m"], sub["coverage_rate"], marker="s", linestyle="--",
                label=f"Cumulative: {combo}")

    ax.set_xlabel("Radius (m)")
    ax.set_ylabel("Coverage Rate")
    ax.set_title(f"Venue Coverage by Radius\n{timestamp_label}")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No data available", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="gray")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fname = "coverage_by_radius.png"
    fig.savefig(output_dir / fname, dpi=150)
    plt.close(fig)
    filenames.append(fname)

    # 2. incremental_coverage.png
    fig, ax = plt.subplots(figsize=(10.67, 6))
    cum_overall = summary_df[
        (summary_df["scope"] == "overall")
        & (summary_df["coverage_kind"] == "cumulative")
    ]
    if not cum_overall.empty:
        combos = cum_overall["source_or_combination"].unique()
        bar_width = 0.8 / max(len(combos), 1)
        for i, combo in enumerate(combos):
            sub = cum_overall[cum_overall["source_or_combination"] == combo]
            x = np.arange(len(radii))
            vals = []
            for r in radii:
                row = sub[sub["radius_m"] == r]
                vals.append(row.iloc[0]["marginal_gain_pp"] if not row.empty else 0)
            ax.bar(x + i * bar_width, vals, bar_width, label=combo)
        ax.set_xticks(x + bar_width * (len(combos) - 1) / 2)
        ax.set_xticklabels([f"{r}m" for r in radii])
    ax.set_xlabel("Radius")
    ax.set_ylabel("Incremental Gain (pp)")
    ax.set_title(f"Incremental Coverage Contribution\n{timestamp_label}")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No data available", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="gray")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fname = "incremental_coverage.png"
    fig.savefig(output_dir / fname, dpi=150)
    plt.close(fig)
    filenames.append(fname)

    # 3. venue_type_coverage_heatmap.png
    fig, ax = plt.subplots(figsize=(10.67, 6))
    vt_data = summary_df[
        (summary_df["scope"] == "venue_type")
        & (summary_df["coverage_kind"] == "standalone")
    ]
    if not vt_data.empty:
        venue_types = sorted(vt_data["group_value"].unique())
        sources_list = sorted(vt_data["source_or_combination"].unique())
        col_labels = []
        for src in sources_list:
            for r in radii:
                col_labels.append(f"{src}\n{r}m")
        matrix = np.zeros((len(venue_types), len(col_labels)))
        for i, vt in enumerate(venue_types):
            for j, src in enumerate(sources_list):
                for k, r in enumerate(radii):
                    row = vt_data[
                        (vt_data["group_value"] == vt)
                        & (vt_data["source_or_combination"] == src)
                        & (vt_data["radius_m"] == r)
                    ]
                    if not row.empty:
                        matrix[i, j * len(radii) + k] = row.iloc[0]["coverage_rate"]

        im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, fontsize=7, rotation=45, ha="right")
        ax.set_yticks(range(len(venue_types)))
        ax.set_yticklabels(venue_types)
        fig.colorbar(im, ax=ax, label="Coverage Rate")
    ax.set_title(f"Venue Type Coverage Heatmap\n{timestamp_label}")
    fig.tight_layout()
    fname = "venue_type_coverage_heatmap.png"
    fig.savefig(output_dir / fname, dpi=150)
    plt.close(fig)
    filenames.append(fname)

    # 4. uncovered_venue_distribution.png
    fig, ax = plt.subplots(figsize=(10.67, 6))
    # Use last radius for uncovered counts by district
    last_r = radii[-1]
    uncovered_data = summary_df[
        (summary_df["scope"] == "district")
        & (summary_df["coverage_kind"] == "standalone")
        & (summary_df["radius_m"] == last_r)
    ].copy()
    if not uncovered_data.empty:
        # Fill NaN group values for sorting/display
        uncovered_data["group_value"] = uncovered_data["group_value"].fillna("(unknown)")
        districts = sorted(uncovered_data["group_value"].unique(), key=str)
        sources_list = sorted(uncovered_data["source_or_combination"].unique())
        x = np.arange(len(districts))
        bar_width = 0.8 / max(len(sources_list), 1)
        for i, src in enumerate(sources_list):
            vals = []
            for d in districts:
                row = uncovered_data[
                    (uncovered_data["group_value"] == d)
                    & (uncovered_data["source_or_combination"] == src)
                ]
                if not row.empty:
                    vals.append(row.iloc[0]["venue_count"] - row.iloc[0]["covered_count"])
                else:
                    vals.append(0)
            ax.bar(x + i * bar_width, vals, bar_width, label=src)
        ax.set_xticks(x + bar_width * (len(sources_list) - 1) / 2)
        ax.set_xticklabels(districts, rotation=30, ha="right")
    ax.set_xlabel("District")
    ax.set_ylabel("Uncovered Venues")
    ax.set_title(f"Uncovered Venue Distribution at {last_r}m\n{timestamp_label}")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No data available", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="gray")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fname = "uncovered_venue_distribution.png"
    fig.savefig(output_dir / fname, dpi=150)
    plt.close(fig)
    filenames.append(fname)

    return filenames


def write_artifacts(
    output_dir: Path,
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    metadata: dict,
    report_md: str,
    chart_filenames: list[str],
) -> None:
    """Write all artifacts directly to output_dir, overwriting previous run."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write CSVs
    detail_df.to_csv(output_dir / "venue_coverage_detail.csv", index=False)
    summary_df.to_csv(output_dir / "coverage_summary.csv", index=False)

    # Write metadata
    with open(output_dir / "run_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # Write report
    with open(output_dir / "coverage_report.md", "w") as f:
        f.write(report_md)

    # Charts are already saved to output_dir by generate_charts

    # Validate completeness
    required_files = [
        "venue_coverage_detail.csv",
        "coverage_summary.csv",
        "run_metadata.json",
        "coverage_report.md",
    ] + chart_filenames

    missing = [f for f in required_files if not (output_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required artifacts: {missing}"
        )

    empty = [f for f in required_files if (output_dir / f).stat().st_size == 0]
    if empty:
        raise ValueError(f"Empty artifacts: {empty}")


# ── Module-level cached transformer for traffic ────────────────
_traffic_transformer = None

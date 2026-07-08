"""forecast_v2_feature_pipeline.py — Dynamic + time feature engineering for forecast-v2.

Builds training samples from busyness_scores with lookback windows, time features,
and venue metadata. Follows the forecast-v2 SOP: tabular baseline only, no ARIMA/LSTM.

Usage:
  python forecast_v2_feature_pipeline.py --dry-run          # build features, no DB write
  python forecast_v2_feature_pipeline.py --output-dir ./output
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import db_utils
from forecast_v2_features import (
    DYNAMIC_FEATURES, TIME_FEATURES, SPATIAL_FEATURES, TRAFFIC_FEATURES,
    WEATHER_FEATURES, HOLIDAY_FEATURES, GBFS_FEATURES, MTA_FEATURES,
    ALL_FEATURES as ALL_FEATURE_COLS,
)
from score_utils import (
    SCORE_CLAMP, BUSY_LEVEL_THRESHOLDS, clamp_score, score_to_level,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE
for _p in [HERE, *HERE.parents]:
    if (_p / "Data+ML").exists() and (_p / "docker").exists():
        PROJECT_ROOT = _p
        break

DB_MODULE = PROJECT_ROOT / "Data+ML/test/6.2-6.5_DB"
if str(DB_MODULE) not in sys.path:
    sys.path.insert(0, str(DB_MODULE))

# ── Constants ─────────────────────────────────────────────────────────────────
HOURS = list(range(24))
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# ── Data loaders ──────────────────────────────────────────────────────────────


def load_venues(max_venues: int = 50) -> pd.DataFrame:
    """Load venues with district, opening_hours, accessible_status, language_tags."""
    return db_utils.read_sql("""
        SELECT venue_id, name, venue_type, latitude, longitude, borough,
               district, opening_hours, accessible_status, language_tags,
               primary_language, secondary_language, rating
        FROM venues
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT %s
    """, (max_venues,))


def load_busyness_scores(max_rows: int = 10000) -> pd.DataFrame:
    return db_utils.read_sql("""
        SELECT venue_id, score, level, forecast_start_time, forecast_end_time,
               model_version, created_at
        FROM busyness_scores
        ORDER BY forecast_start_time ASC
        LIMIT %s
    """, (max_rows,))


def load_user_reports() -> pd.DataFrame:
    return db_utils.read_sql("""
        SELECT report_id, venue_id, issue_type, status, created_at, expires_at
        FROM user_reports
        WHERE venue_id IS NOT NULL AND status = 'active'
        ORDER BY created_at ASC
    """)


def load_busyness_forecasts() -> pd.DataFrame:
    return db_utils.read_sql("""
        SELECT venue_id, forecast_for, predicted_score, predicted_level, model_version
        FROM busyness_forecasts
        ORDER BY forecast_for ASC
    """)


def load_weather_cache() -> dict[str, Any] | None:
    """Load latest weather from external_context_cache."""
    return db_utils.load_from_cache("weather_forecast")


def load_external_features() -> dict[str, dict[str, Any]]:
    """Load ALL external features from DB cache."""
    sources = {"weather": ("weather_forecast", WEATHER_FALLBACK),
               "holiday": ("public_holidays", HOLIDAY_FALLBACK),
               "gbfs": ("gbfs_station_status", GBFS_FALLBACK),
               "mta": ("mta_realtime", MTA_FALLBACK)}
    result: dict[str, dict[str, Any]] = {}
    for name, (ctx_type, fallback) in sources.items():
        payload = db_utils.load_from_cache(ctx_type)
        result[name] = {"payload": payload or fallback.copy(),
                        "available": payload is not None}
    return result


def load_mta_stations() -> pd.DataFrame:
    """Load MTA subway stations → station_id, station_name, lat, lon."""
    path = PROJECT_ROOT / "data_source" / "MTA_Subway_Stations_20260526.csv"
    if not path.exists():
        return pd.DataFrame(columns=["station_id", "latitude", "longitude"])
    raw = pd.read_csv(path)
    stations = raw.rename(columns={
        "GTFS Stop ID": "station_id",
        "GTFS Latitude": "latitude",
        "GTFS Longitude": "longitude",
    })[["station_id", "latitude", "longitude"]].dropna(subset=["latitude", "longitude"])
    bbox = {"lat_min": 40.45, "lat_max": 41.05, "lon_min": -74.35, "lon_max": -73.55}
    stations = stations[
        stations["latitude"].between(bbox["lat_min"], bbox["lat_max"])
        & stations["longitude"].between(bbox["lon_min"], bbox["lon_max"])
    ]
    return stations


def load_citibike_stations() -> pd.DataFrame:
    """Load Citi Bike stations from GBFS JSON."""
    import json
    path = PROJECT_ROOT / "data_source" / "citibike_station_information.json"
    if not path.exists():
        return pd.DataFrame(columns=["station_id", "latitude", "longitude"])
    data = json.loads(path.read_text())
    stations = pd.DataFrame(data.get("data", {}).get("stations", []))
    if not {"station_id", "lat", "lon"}.issubset(stations.columns):
        return pd.DataFrame(columns=["station_id", "latitude", "longitude"])
    stations = stations.rename(columns={"lat": "latitude", "lon": "longitude"})
    return stations[["station_id", "latitude", "longitude"]].dropna(subset=["latitude", "longitude"])


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two (lat, lon) pairs."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(6371000 * 2 * np.arcsin(np.sqrt(a)))


def nearest_distance_m(lat: float, lon: float, points: np.ndarray) -> float:
    """Nearest haversine distance from (lat, lon) to any point in `points` array (N, 2)."""
    if len(points) == 0:
        return 9999.0
    d = 6371000 * 2 * np.arcsin(np.sqrt(
        np.sin((np.radians(points[:, 0]) - np.radians(lat)) / 2) ** 2
        + np.cos(np.radians(lat)) * np.cos(np.radians(points[:, 0]))
        * np.sin((np.radians(points[:, 1]) - np.radians(lon)) / 2) ** 2
    ))
    return float(np.min(d))


def build_venue_spatial_features(venues: pd.DataFrame,
                                  mta: pd.DataFrame,
                                  citibike: pd.DataFrame) -> pd.DataFrame:
    """Compute nearest MTA and Citi Bike distances for each venue."""
    mta_pts = mta[["latitude", "longitude"]].to_numpy(dtype=float) if len(mta) else np.empty((0, 2))
    cb_pts = citibike[["latitude", "longitude"]].to_numpy(dtype=float) if len(citibike) else np.empty((0, 2))
    rows = []
    for _, v in venues.iterrows():
        rows.append({
            "venue_id": v["venue_id"],
            "nearest_mta_distance_m": round(nearest_distance_m(v["latitude"], v["longitude"], mta_pts), 1),
            "nearest_citibike_distance_m": round(nearest_distance_m(v["latitude"], v["longitude"], cb_pts), 1),
        })
    return pd.DataFrame(rows)


def build_district_hourly_traffic(scores: pd.DataFrame, venues: pd.DataFrame) -> pd.DataFrame:
    """Aggregate busyness_scores by (district, hour) → district average traffic proxy."""
    if scores.empty or "district" not in scores.columns:
        merged = scores.merge(venues[["venue_id", "district"]], on="venue_id", how="left")
    else:
        merged = scores.copy()
        if "district" not in merged.columns:
            merged = merged.merge(venues[["venue_id", "district"]], on="venue_id", how="left")
    merged["hour"] = pd.to_datetime(merged["forecast_start_time"]).dt.hour
    return (
        merged.groupby(["district", "hour"])["score"]
        .mean().reset_index()
        .rename(columns={"score": "district_traffic_score"})
    )


def build_district_density_lookup(scores: pd.DataFrame, venues: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], int]:
    """Precompute district_live_density for each (district, ref_time).

    For a sample at ref_time, district_live_density counts venues in the same
    district with scores in [ref_time - 1h, ref_time). With hourly score rows,
    that is the previous score hour shifted forward by one hour.
    """
    if scores.empty or venues.empty:
        return {}
    merged = scores.merge(venues[["venue_id", "district"]], on="venue_id", how="left")
    merged = merged.dropna(subset=["district", "forecast_start_time"])
    if merged.empty:
        return {}
    merged["density_ref_time"] = pd.to_datetime(merged["forecast_start_time"]) + pd.Timedelta(hours=1)
    grouped = (
        merged.groupby(["district", "density_ref_time"])["venue_id"]
        .nunique()
        .reset_index(name="live_count")
    )
    return {
        (str(r["district"]), pd.Timestamp(r["density_ref_time"])): int(r["live_count"])
        for _, r in grouped.iterrows()
    }


# ── Synthetic data generators (for testing without DB) ────────────────────────


def _synth_venues(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    districts = ["Midtown", "Downtown", "Upper_East", "Upper_West", "Harlem", "Chelsea", "SoHo", "Financial_District"]
    types = ["clinic", "pharmacy", "hospital", "dentist", "laboratory", "restroom"]
    hours_options = [
        "9 AM–5 PM",
        "8 AM–8 PM",
        "Mo-Fr 08:00-18:00; Sa 09:00-14:00",
        "Open 24 hours",
        "8 AM–10 PM",
    ]
    rows = []
    for i in range(n):
        rows.append({
            "venue_id": f"v_{1000 + i}",
            "name": f"Test Venue {i}",
            "venue_type": types[i % len(types)],
            "latitude": round(rng.uniform(40.70, 40.82), 6),
            "longitude": round(rng.uniform(-74.02, -73.90), 6),
            "borough": "Manhattan",
            "district": districts[i % len(districts)],
            "opening_hours": hours_options[i % len(hours_options)],
            "accessible_status": ["full_access", "partial", "none"][i % 3],
            "language_tags": '["EN"]',
            "primary_language": "EN",
            "secondary_language": None,
            "rating": round(rng.uniform(2.0, 5.0), 1),
        })
    return pd.DataFrame(rows)


def _synth_scores(venues: pd.DataFrame, hours_back: int = 168) -> pd.DataFrame:
    """Generate synthetic hourly scores for each venue going back `hours_back` hours."""
    rng = np.random.default_rng(42)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = []
    for _, v in venues.iterrows():
        base_score = rng.uniform(20, 80)
        for h in range(hours_back):
            ts = now - timedelta(hours=h)
            hour = ts.hour
            # Add diurnal pattern
            if 8 <= hour <= 18:
                score = base_score + 15 * np.sin(np.pi * (hour - 8) / 10) + rng.normal(0, 5)
            else:
                score = base_score * 0.4 + rng.normal(0, 3)
            score = max(0, min(100, score))
            rows.append({
                "venue_id": v["venue_id"],
                "score": round(score),
                "level": score_to_level(score),
                "forecast_start_time": ts,
                "forecast_end_time": ts + timedelta(hours=12),
                "model_version": "nyc_traffic_baseline_v1",
                "created_at": ts,
            })
    return pd.DataFrame(rows).sort_values("forecast_start_time")


def _synth_reports(scores: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    venues = scores["venue_id"].unique()
    times = sorted(scores["forecast_start_time"].unique())
    for _ in range(len(scores) // 10):
        v = rng.choice(venues)
        t = rng.choice(times)
        rows.append({
            "report_id": f"r_{len(rows):06d}",
            "venue_id": v,
            "issue_type": "crowded",
            "status": "active",
            "created_at": t,
            "expires_at": t + timedelta(hours=2),
        })
    return pd.DataFrame(rows)


# ── Opening hours parsing ────────────────────────────────────────────────────
# Parses free-text venues.opening_hours into per-day (open_h, close_h) intervals.
# Supports: "9 AM–5 PM", "Mo-Fr 08:00-18:00; Sa 09:00-14:00", "Open 24 hours", etc.


def _parse_clock_time(value: str, fallback_period: str | None = None) -> float | None:
    """Parse a clock-time string like '8:30 AM' → 8.5 (float hours)."""
    text = value.strip().upper().replace(".", "")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AP]M)?", text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    period = m.group(3) or fallback_period
    if period not in {"AM", "PM"}:
        return None
    if hour == 12:
        hour = 0
    if period == "PM":
        hour += 12
    return hour + minute / 60


def _parse_hours_interval(text: str) -> tuple[float, float] | None:
    """Parse a single hours range like '8:30 AM–6:30 PM' → (8.5, 18.5)."""
    normalized = (
        text.replace("–", "-").replace("—", "-")
        .replace("−", "-").replace(" to ", "-")
    )
    if "-" not in normalized:
        return None
    start_text, end_text = [p.strip() for p in normalized.split("-", 1)]
    end_period_m = re.search(r"([AP]M)\b", end_text.upper())
    fallback = end_period_m.group(1) if end_period_m else None
    start = _parse_clock_time(start_text, fallback_period=fallback)
    end = _parse_clock_time(end_text)
    if start is None or end is None:
        return None
    return start, end


def parse_opening_hours(raw: object) -> dict[str, Any]:
    """Parse a venues.opening_hours free-text value → {status, per_day_intervals}.

    Returns:
        {"status": "open_24h"|"closed"|"parsed"|"unknown",
         "intervals": {day_index: [(open_h, close_h), ...]}}
    """
    if not isinstance(raw, str) or not raw.strip():
        return {"status": "unknown", "intervals": {}}

    text = raw.strip()
    lowered = text.lower()

    if "open 24 hours" in lowered or lowered == "24 hours":
        return {"status": "open_24h", "intervals": {}}

    if lowered in {"closed", "temporarily closed"}:
        return {"status": "closed", "intervals": {}}

    # Try OSM-style: "Mo-Fr 08:00-18:00; Sa, Su 09:00-14:00"
    day_map = {"mo": 0, "tu": 1, "we": 2, "th": 3, "fr": 4, "sa": 5, "su": 6,
               "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    long_day = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6}

    # Split on ";" or "," that separates day-blocks (not commas inside "Sa, Su")
    blocks = re.split(r";\s*", text)
    per_day: dict[int, list[tuple[float, float]]] = {}

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Separate day-spec from time-spec: find where the time starts
        time_m = re.search(r"\d{1,2}[:\d]*\s*([AP]M)?", block)
        if not time_m:
            # No time found — try parsing whole block as a single interval
            interval = _parse_hours_interval(block)
            if interval:
                for d in range(7):
                    per_day.setdefault(d, []).append(interval)
            continue

        day_part = block[:time_m.start()].strip().rstrip(",").strip()
        time_part = block[time_m.start():].strip()

        # Parse day list: "Mo-Fr" or "Sa, Su" or "Mo"
        day_indices: list[int] = []
        for token in re.split(r",\s*", day_part):
            token = token.strip().lower()
            if "-" in token:
                parts = token.split("-", 1)
                start_d = day_map.get(parts[0].strip()) or long_day.get(parts[0].strip())
                end_d = day_map.get(parts[1].strip()) or long_day.get(parts[1].strip())
                if start_d is not None and end_d is not None:
                    if end_d >= start_d:
                        day_indices.extend(range(start_d, end_d + 1))
                    else:
                        day_indices.extend(range(start_d, 7))
                        day_indices.extend(range(0, end_d + 1))
            else:
                d = day_map.get(token) or long_day.get(token)
                if d is not None:
                    day_indices.append(d)

        # If no days parsed, apply to all days
        if not day_indices:
            day_indices = list(range(7))

        # Parse time intervals in the time part (may be comma-separated)
        interval = _parse_hours_interval(time_part)
        if interval:
            for d in day_indices:
                per_day.setdefault(d, []).append(interval)

    if not per_day:
        # Fallback: try parsing whole text as a single daily interval
        interval = _parse_hours_interval(text)
        if interval:
            for d in range(7):
                per_day[d] = [interval]
            return {"status": "parsed", "intervals": per_day}
        return {"status": "unknown", "intervals": {}}

    return {"status": "parsed", "intervals": per_day}


def build_venue_hours_lookup(venues: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Parse opening_hours for every venue → {venue_id: parsed_hours}."""
    lookup: dict[str, dict[str, Any]] = {}
    for _, v in venues.iterrows():
        lookup[v["venue_id"]] = parse_opening_hours(v.get("opening_hours"))
    return lookup


def _is_open_at(hours_info: dict[str, Any], day_index: int, hour: float) -> bool:
    """Check if venue is open at a given (day_index, hour).

    Falls back to 8AM-8PM heuristic when hours_info is unavailable or unparseable.
    """
    status = hours_info.get("status", "unknown")
    if status == "open_24h":
        return True
    if status == "closed":
        return False
    intervals = hours_info.get("intervals", {}).get(day_index, [])
    if intervals:
        for start, end in intervals:
            if start <= end:
                if start <= hour < end:
                    return True
            else:  # overnight
                if hour >= start or hour < end:
                    return True
        return False
    # Fallback: 8AM-8PM heuristic
    return 8 <= hour < 20


def _minutes_until_close(hours_info: dict[str, Any], day_index: int, hour: float) -> float:
    """Minutes until the next closing time. Falls back to 8PM close time."""
    status = hours_info.get("status", "unknown")
    if status == "open_24h":
        return 9999.0
    if status == "closed":
        return 0.0
    intervals = hours_info.get("intervals", {}).get(day_index, [])
    if intervals:
        best = None
        for start, end in intervals:
            if start <= end:
                if start <= hour < end:
                    remaining = (end - hour) * 60
                    best = min(best, remaining) if best is not None else remaining
            else:
                if hour >= start:
                    remaining = (24 - hour + end) * 60
                    best = min(best, remaining) if best is not None else remaining
                elif hour < end:
                    remaining = (end - hour) * 60
                    best = min(best, remaining) if best is not None else remaining
        return best if best is not None else 0.0
    # Fallback: close at 20:00
    if hour < 20:
        return max(0, (20 - hour) * 60)
    return 0.0


def _minutes_since_open(hours_info: dict[str, Any], day_index: int, hour: float) -> float:
    """Minutes since the most recent opening time. Falls back to 8AM open time."""
    status = hours_info.get("status", "unknown")
    if status == "open_24h":
        return 9999.0
    if status == "closed":
        return 0.0
    intervals = hours_info.get("intervals", {}).get(day_index, [])
    if intervals:
        best = None
        for start, end in intervals:
            if start <= end:
                if start <= hour < end:
                    elapsed = (hour - start) * 60
                    best = min(best, elapsed) if best is not None else elapsed
            else:
                if hour >= start:
                    elapsed = (hour - start) * 60
                    best = min(best, elapsed) if best is not None else elapsed
                elif hour < end:
                    elapsed = (24 - start + hour) * 60
                    best = min(best, elapsed) if best is not None else elapsed
        return best if best is not None else 0.0
    # Fallback: open at 8:00
    if hour >= 8:
        return max(0, (hour - 8) * 60)
    return 0.0


# ── Feature builders ──────────────────────────────────────────────────────────


def _build_lookback_cache(scores: pd.DataFrame) -> pd.DataFrame:
    """Pre-sort scores and add lookback index for fast window queries."""
    df = scores.copy()
    df = df.sort_values(["venue_id", "forecast_start_time"])
    return df


def compute_dynamic_features(
    venue_id: str,
    ref_time: pd.Timestamp,
    scores_cache: pd.DataFrame,
    reports_cache: pd.DataFrame,
    venues_meta: pd.DataFrame,
    district_density_lookup: dict[tuple[str, pd.Timestamp], int] | None = None,
) -> dict[str, Any]:
    """Compute all dynamic features for a (venue_id, ref_time) sample.

    All features use only data strictly BEFORE ref_time (no future leakage).
    Missing values are explicitly filled with sentinels + missing flags.
    """
    feats: dict[str, Any] = {}

    # Normalise tz: strip tzinfo from ref_time if scores are tz-naive
    _ref = ref_time
    if not scores_cache.empty:
        sample_ts = scores_cache["forecast_start_time"].iloc[0]
        if hasattr(sample_ts, 'tzinfo') and sample_ts.tzinfo is None and _ref.tzinfo is not None:
            _ref = _ref.tz_localize(None)
        elif hasattr(sample_ts, 'tzinfo') and sample_ts.tzinfo is not None and _ref.tzinfo is None:
            _ref = _ref.tz_localize('UTC')

    # --- Scores for this venue before ref_time ---
    v_scores = scores_cache[
        (scores_cache["venue_id"] == venue_id)
        & (scores_cache["forecast_start_time"] < _ref)
    ]
    v_scores = v_scores.sort_values("forecast_start_time")

    # latest_busyness_score + age
    if not v_scores.empty:
        latest = v_scores.iloc[-1]
        feats["latest_busyness_score"] = float(latest["score"])
        age_minutes = (_ref - latest["forecast_start_time"]).total_seconds() / 60
        feats["latest_busyness_age_minutes"] = max(0.0, age_minutes)
        feats["latest_score_missing"] = 0
    else:
        feats["latest_busyness_score"] = -1.0
        feats["latest_busyness_age_minutes"] = 9999.0
        feats["latest_score_missing"] = 1

    # rolling windows
    for window_h in [1, 3]:
        cutoff = _ref - timedelta(hours=window_h)
        window = v_scores[v_scores["forecast_start_time"] >= cutoff]
        if not window.empty:
            feats[f"rolling_mean_{window_h}h"] = float(window["score"].mean())
            feats[f"rolling_mean_{window_h}h_missing"] = 0
        else:
            feats[f"rolling_mean_{window_h}h"] = -1.0
            feats[f"rolling_mean_{window_h}h_missing"] = 1

    # rolling_max_3h
    cutoff_3h = _ref - timedelta(hours=3)
    window_3h = v_scores[v_scores["forecast_start_time"] >= cutoff_3h]
    if not window_3h.empty:
        feats["rolling_max_3h"] = float(window_3h["score"].max())
        feats["rolling_max_3h_missing"] = 0
    else:
        feats["rolling_max_3h"] = -1.0
        feats["rolling_max_3h_missing"] = 1

    # --- Reports for this venue before ref_time ---
    v_reports = reports_cache[
        (reports_cache["venue_id"] == venue_id)
        & (reports_cache["created_at"] < _ref)
    ] if not reports_cache.empty else pd.DataFrame()

    for window_h in [1, 3]:
        cutoff = _ref - timedelta(hours=window_h)
        count = len(v_reports[v_reports["created_at"] >= cutoff]) if not v_reports.empty else 0
        feats[f"recent_report_count_{window_h}h"] = count
        feats[f"recent_report_count_{window_h}h_missing"] = 0 if not v_reports.empty else 1

    # active_report_severity_score: count of recent reports weighted by recency
    if not v_reports.empty:
        recent = v_reports[v_reports["created_at"] >= _ref - timedelta(hours=6)]
        if not recent.empty:
            hours_ago = (_ref - recent["created_at"]).dt.total_seconds() / 3600
            feats["active_report_severity_score"] = float((1.0 / (1.0 + hours_ago)).sum())
            feats["active_report_severity_score_missing"] = 0
        else:
            feats["active_report_severity_score"] = 0.0
            feats["active_report_severity_score_missing"] = 0
    else:
        feats["active_report_severity_score"] = 0.0
        feats["active_report_severity_score_missing"] = 1

    # --- district_live_density: number of venues with recent scores in same district ---
    venue_row = venues_meta[venues_meta["venue_id"] == venue_id]
    district = venue_row.iloc[0]["district"] if not venue_row.empty else None
    if district is not None:
        if district_density_lookup is not None:
            live_count = district_density_lookup.get((str(district), pd.Timestamp(_ref)), 0)
        else:
            district_scores = scores_cache[
                (scores_cache["forecast_start_time"] >= _ref - timedelta(hours=1))
                & (scores_cache["forecast_start_time"] < _ref)
            ]
            district_venues = venues_meta[venues_meta["district"] == district]
            district_venue_ids = set(district_venues["venue_id"])
            live_count = district_scores[district_scores["venue_id"].isin(district_venue_ids)]["venue_id"].nunique()
        feats["district_live_density"] = live_count
        feats["district_live_density_missing"] = 0
    else:
        feats["district_live_density"] = -1
        feats["district_live_density_missing"] = 1

    # --- venue_capacity_bucket: from venue_type/rating as proxy ---
    vtype = venue_row.iloc[0]["venue_type"] if not venue_row.empty else "unknown"
    rating = venue_row.iloc[0].get("rating") if not venue_row.empty else None
    if vtype in ("hospital",):
        bucket = 3
    elif vtype in ("clinic", "pharmacy"):
        bucket = 2
    else:
        bucket = 1
    feats["venue_capacity_bucket"] = bucket

    return feats


# Exported feature name lists (used by model + tests)
# ── Feature lists ── (all imported from forecast_v2_features:
#   DYNAMIC_FEATURES, TIME_FEATURES, SPATIAL_FEATURES, TRAFFIC_FEATURES,
#   WEATHER_FEATURES, HOLIDAY_FEATURES, GBFS_FEATURES, MTA_FEATURES, ALL_FEATURE_COLS)

# ── External feature fallbacks ────────────────────────────────────────────────
WEATHER_FALLBACK = {
    "temperature_c": -999, "temperature_missing": True,
    "humidity_pct": -1, "humidity_missing": True,
    "wind_speed_kmh": -1, "wind_missing": True,
    "precipitation_mm": 0.0, "precipitation_missing": True,
    "weather_condition": "unknown", "weather_code": -1,
    "heat_alert": 0, "heat_alert_missing": True,
    "weather_source": "unavailable",
}
HOLIDAY_FALLBACK = {
    "is_public_holiday": 0, "holiday_missing": True,
    "is_major_event_nearby": 0, "event_distance_km": -1,
    "event_source": "unavailable", "holidays_today": [],
}
GBFS_FALLBACK = {
    "citibike_station_activity": 0, "citibike_activity_missing": True,
    "nearby_bike_availability": 0, "nearby_dock_availability": 0,
    "gbfs_source": "unavailable",
}
MTA_FALLBACK = {
    "mta_service_disruption_flag": 0, "mta_disruption_missing": True,
    "mta_realtime_arrival_count_1h": 0, "mta_arrival_missing": True,
    "mta_source": "unavailable",
}


def compute_time_features(
    ref_time: pd.Timestamp,
    offset_hours: int = 0,
    hours_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute time features for the target prediction hour (ref_time + offset_hours).

    Uses parsed venue opening_hours for is_business_hours, minutes_until_close,
    minutes_since_open, and availability_penalty. Falls back to 8AM-8PM heuristic
    only when hours_info is missing or unparseable.
    """
    target = ref_time + timedelta(hours=offset_hours)
    day_idx = target.weekday()
    target_h = float(target.hour)

    if hours_info is None:
        hours_info = {"status": "unknown", "intervals": {}}

    is_open = _is_open_at(hours_info, day_idx, target_h)
    mins_to_close = _minutes_until_close(hours_info, day_idx, target_h)
    mins_since_open = _minutes_since_open(hours_info, day_idx, target_h)
    avail_penalty = 0 if is_open else 1

    return {
        "hour_of_day": ref_time.hour,
        "day_of_week": DAYS[target.weekday()],
        "day_of_week_index": target.weekday(),
        "is_weekend": 1 if target.weekday() >= 5 else 0,
        "is_business_hours": 1 if is_open else 0,
        "time_bucket": _time_bucket(target.hour),
        "forecast_offset_hours": offset_hours,
        "target_hour_of_day": target.hour,
        "target_day_of_week": DAYS[target.weekday()],
        "minutes_until_close": round(mins_to_close, 1),
        "minutes_since_open": round(mins_since_open, 1),
        "is_holiday_or_event_stub": 0,
        "availability_penalty": avail_penalty,
    }


def _time_bucket(hour: int) -> str:
    if 0 <= hour < 6:
        return "night"
    elif 6 <= hour < 9:
        return "morning_rush"
    elif 9 <= hour < 12:
        return "morning"
    elif 12 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 20:
        return "evening_rush"
    else:
        return "night"


# ── Main feature builder ──────────────────────────────────────────────────────


def build_training_samples(
    scores: pd.DataFrame,
    venues: pd.DataFrame,
    reports: pd.DataFrame | None = None,
    max_samples_per_venue: int = 200,
    use_real_external: bool = False,
) -> pd.DataFrame:
    """Build the full training table: one row per (venue_id, forecast_start_time).

    Each row = dynamic features (from lookback) + time features (from forecast_start_time) + label (score).
    """
    if reports is None:
        reports = pd.DataFrame()

    scores_cache = _build_lookback_cache(scores)
    venues_indexed = venues.set_index("venue_id")
    venue_hours = build_venue_hours_lookup(venues)

    # Pre-compute supplementary features
    spatial_feats = build_venue_spatial_features(venues, load_mta_stations(), load_citibike_stations()) if _has_data_sources() else _synth_spatial_features(venues)
    district_traffic = build_district_hourly_traffic(scores, venues)
    ext_feats = _collect_external_features(synth=not use_real_external)

    all_rows: list[dict[str, Any]] = []
    venue_ids = scores["venue_id"].unique()

    for vid in venue_ids:
        v_scores = scores[scores["venue_id"] == vid].sort_values("forecast_start_time")
        if len(v_scores) > max_samples_per_venue:
            indices = np.linspace(0, len(v_scores) - 1, max_samples_per_venue, dtype=int)
            v_scores = v_scores.iloc[indices]

        h_info = venue_hours.get(vid, {"status": "unknown", "intervals": {}})
        spat = spatial_feats[spatial_feats["venue_id"] == vid].iloc[0] if len(spatial_feats[spatial_feats["venue_id"] == vid]) else {}
        v_district = venues_indexed.loc[vid, "district"] if vid in venues_indexed.index else None

        for _, row in v_scores.iterrows():
            ref_time = row["forecast_start_time"]
            if isinstance(ref_time, datetime):
                ref_time = pd.Timestamp(ref_time)
            target_hour = ref_time.hour

            dynamic = compute_dynamic_features(vid, ref_time, scores_cache, reports, venues_indexed.reset_index())
            time_feats = compute_time_features(ref_time, offset_hours=0, hours_info=h_info)

            # District traffic score
            dt_row = district_traffic[(district_traffic["district"] == v_district) & (district_traffic["hour"] == target_hour)]
            traffic_score = float(dt_row.iloc[0]["district_traffic_score"]) if len(dt_row) else -1.0

            sample = {
                "venue_id": vid,
                "forecast_for": ref_time,
                "offset_hours": 0,
                **dynamic,
                **time_feats,
                "nearest_mta_distance_m": spat.get("nearest_mta_distance_m", -1),
                "nearest_citibike_distance_m": spat.get("nearest_citibike_distance_m", -1),
                "district_traffic_score": traffic_score,
                **ext_feats,
                "label_score": int(row["score"]),
                "label_level": row["level"],
            }
            all_rows.append(sample)

    return pd.DataFrame(all_rows)


def build_prediction_samples(
    venues: pd.DataFrame,
    scores: pd.DataFrame,
    reports: pd.DataFrame | None = None,
    forecast_base_time: datetime | None = None,
    use_real_external: bool = False,
) -> pd.DataFrame:
    """Build feature rows for prediction: 12h horizon for every venue.

    Each row = (venue_id, forecast_for = base_time, offset_hours in 0..11).
    """
    if reports is None:
        reports = pd.DataFrame()

    if forecast_base_time is None:
        forecast_base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    scores_cache = _build_lookback_cache(scores)
    venues_indexed = venues.set_index("venue_id")
    venue_hours = build_venue_hours_lookup(venues)

    spatial_feats = build_venue_spatial_features(venues, load_mta_stations(), load_citibike_stations()) if _has_data_sources() else _synth_spatial_features(venues)
    district_traffic = build_district_hourly_traffic(scores, venues)
    ext_feats = _collect_external_features(synth=not use_real_external)

    all_rows: list[dict[str, Any]] = []
    for _, v in venues.iterrows():
        vid = v["venue_id"]
        ref_time = pd.Timestamp(forecast_base_time)
        h_info = venue_hours.get(vid, {"status": "unknown", "intervals": {}})
        spat = spatial_feats[spatial_feats["venue_id"] == vid].iloc[0] if len(spatial_feats[spatial_feats["venue_id"] == vid]) else {}
        v_district = v.get("district")

        for offset in range(12):
            dynamic = compute_dynamic_features(vid, ref_time, scores_cache, reports, venues_indexed.reset_index())
            time_feats = compute_time_features(ref_time, offset_hours=offset, hours_info=h_info)

            target_hour = (ref_time + timedelta(hours=offset)).hour
            dt_row = district_traffic[(district_traffic["district"] == v_district) & (district_traffic["hour"] == target_hour)]
            traffic_score = float(dt_row.iloc[0]["district_traffic_score"]) if len(dt_row) else -1.0

            sample = {
                "venue_id": vid,
                "forecast_for": ref_time,
                "offset_hours": offset,
                **dynamic,
                **time_feats,
                "nearest_mta_distance_m": spat.get("nearest_mta_distance_m", -1),
                "nearest_citibike_distance_m": spat.get("nearest_citibike_distance_m", -1),
                "district_traffic_score": traffic_score,
                **ext_feats,
            }
            all_rows.append(sample)

    return pd.DataFrame(all_rows)


# ── Synthetic data pipeline (for testing without DB) ──────────────────────────

def _has_data_sources() -> bool:
    """Check if real MTA/Citi Bike data files exist on disk."""
    mta = PROJECT_ROOT / "data_source" / "MTA_Subway_Stations_20260526.csv"
    cb = PROJECT_ROOT / "data_source" / "citibike_station_information.json"
    return mta.exists() and cb.exists()


def _synth_spatial_features(venues: pd.DataFrame) -> pd.DataFrame:
    """Synthetic MTA/Citi Bike distances for testing."""
    rng = np.random.default_rng(42)
    return pd.DataFrame([
        {"venue_id": v["venue_id"],
         "nearest_mta_distance_m": round(rng.uniform(50, 800), 1),
         "nearest_citibike_distance_m": round(rng.uniform(30, 600), 1)}
        for _, v in venues.iterrows()
    ])


def _synth_external_feats() -> dict[str, Any]:
    """Synthetic external features for testing (no DB needed)."""
    return {
        # weather
        "temperature_c": 22.0, "temperature_missing": False,
        "humidity_pct": 55.0, "humidity_missing": False,
        "wind_speed_kmh": 10.0, "wind_missing": False,
        "precipitation_mm": 0.0, "precipitation_missing": False,
        "weather_condition": "clear", "heat_alert": 0, "heat_alert_missing": False,
        "weather_source": "synthetic",
        # holiday
        "is_public_holiday": 0, "holiday_missing": True,
        "is_major_event_nearby": 0, "event_distance_km": -1, "event_source": "unavailable",
        # gbfs
        "citibike_station_activity": 0, "citibike_activity_missing": True,
        "nearby_bike_availability": 0, "nearby_dock_availability": 0, "gbfs_source": "unavailable",
        # mta
        "mta_service_disruption_flag": 0, "mta_disruption_missing": True,
        "mta_realtime_arrival_count_1h": 0, "mta_arrival_missing": True, "mta_source": "unavailable",
    }


_EXTRACT_MAP = {
    # (source_key, payload_key) → flat feature keys
    "weather": {
        "temperature_c": ("temperature_c", -999), "temperature_missing": ("temperature_missing", True),
        "humidity_pct": ("humidity_pct", -1), "humidity_missing": ("humidity_missing", True),
        "wind_speed_kmh": ("wind_speed_kmh", -1), "wind_missing": ("wind_missing", True),
        "precipitation_mm": ("precipitation_mm", 0.0), "precipitation_missing": ("precipitation_missing", True),
        "weather_condition": ("weather_condition", "unknown"), "heat_alert": ("heat_alert", 0),
        "heat_alert_missing": ("heat_alert_missing", True), "weather_source": ("weather_source", "unavailable"),
    },
    "holiday": {
        "is_public_holiday": ("is_public_holiday", 0), "holiday_missing": ("holiday_missing", True),
        "is_major_event_nearby": ("is_major_event_nearby", 0), "event_distance_km": ("event_distance_km", -1),
        "event_source": ("event_source", "unavailable"),
    },
    "gbfs": {
        "citibike_station_activity": ("citibike_station_activity", 0),
        "citibike_activity_missing": ("citibike_activity_missing", True),
        "nearby_bike_availability": ("nearby_bike_availability", 0),
        "nearby_dock_availability": ("nearby_dock_availability", 0),
        "gbfs_source": ("gbfs_source", "unavailable"),
    },
    "mta": {
        "mta_service_disruption_flag": ("mta_service_disruption_flag", 0),
        "mta_disruption_missing": ("mta_disruption_missing", True),
        "mta_realtime_arrival_count_1h": ("mta_realtime_arrival_count_1h", 0),
        "mta_arrival_missing": ("mta_arrival_missing", True),
        "mta_source": ("mta_source", "unavailable"),
    },
}


def _extract_feats(payload: dict[str, Any], source: str) -> dict[str, Any]:
    """Extract standardized feature keys from a source payload dict."""
    return {feat_key: payload.get(payload_key, default)
            for feat_key, (payload_key, default) in _EXTRACT_MAP.get(source, {}).items()}


def _collect_external_features(synth: bool = True) -> dict[str, Any]:
    """Collect all external features: synthetic (default) or from DB cache."""
    if synth:
        return _synth_external_feats()

    ext = load_external_features()
    result: dict[str, Any] = {}
    for src_name, fallback in [("weather", WEATHER_FALLBACK), ("holiday", HOLIDAY_FALLBACK),
                                ("gbfs", GBFS_FALLBACK), ("mta", MTA_FALLBACK)]:
        info = ext.get(src_name, {})
        payload = info.get("payload", fallback)
        result.update(_extract_feats(payload, src_name))
    return result


def build_synthetic_data(
    n_venues: int = 30,
    hours_back: int = 168,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic venues, scores, and reports for testing."""
    np.random.seed(seed)
    venues = _synth_venues(n_venues)
    scores = _synth_scores(venues, hours_back)
    reports = _synth_reports(scores)
    return venues, scores, reports


# ── Missing-value audit ───────────────────────────────────────────────────────


def summarize_missing(frame: pd.DataFrame) -> pd.DataFrame:
    """Return per-column missing rate for all feature columns."""
    feature_cols = [c for c in frame.columns if c not in ("venue_id", "forecast_for", "label_score", "label_level")]
    rows = []
    for col in sorted(feature_cols):
        nulls = frame[col].isna().sum()
        total = len(frame)
        rows.append({
            "column": col,
            "null_count": int(nulls),
            "total": total,
            "missing_pct": round(nulls / total * 100, 1),
        })
    return pd.DataFrame(rows)


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="forecast-v2 feature pipeline")
    p.add_argument("--dry-run", action="store_true", default=True,
                   help="Use synthetic data (default, no DB needed)")
    p.add_argument("--live-db", action="store_true",
                   help="Read from real MySQL DB")
    p.add_argument("--output-dir", type=Path,
                   default=HERE / "output",
                   help="Output directory for feature CSV")
    p.add_argument("--n-synth-venues", type=int, default=30)
    p.add_argument("--synth-hours-back", type=int, default=168)
    p.add_argument("--max-score-rows", type=int, default=200000,
                   help="Maximum busyness_scores rows to read in --live-db mode")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.live_db:
        print("Loading data from DB...")
        venues = load_venues(max_venues=args.n_synth_venues)
        scores = load_busyness_scores(max_rows=args.max_score_rows)
        try:
            reports = load_user_reports()
        except Exception:
            reports = pd.DataFrame()
    else:
        print(f"Generating synthetic data: {args.n_synth_venues} venues, {args.synth_hours_back}h history")
        venues, scores, reports = build_synthetic_data(
            n_venues=args.n_synth_venues,
            hours_back=args.synth_hours_back,
        )

    print(f"  venues: {len(venues)}")
    print(f"  scores: {len(scores)}")
    print(f"  reports: {len(reports)}")

    # Build training samples
    print("\nBuilding training samples...")
    training = build_training_samples(scores, venues, reports, use_real_external=args.live_db)
    print(f"  training rows: {len(training)}")

    # Build prediction samples (for 12h forecast generation)
    print("\nBuilding prediction samples (12h horizon)...")
    pred_samples = build_prediction_samples(venues, scores, reports, use_real_external=args.live_db)
    print(f"  prediction rows: {len(pred_samples)}")

    # Missing value audit
    missing = summarize_missing(training)
    print(f"\nMissing value summary:")
    print(missing[missing["missing_pct"] > 0].to_string(index=False))

    # Save
    train_path = args.output_dir / "forecast_v2_training_features.csv"
    pred_path = args.output_dir / "forecast_v2_prediction_features.csv"
    missing_path = args.output_dir / "forecast_v2_feature_missing_audit.csv"

    training.to_csv(train_path, index=False)
    pred_samples.to_csv(pred_path, index=False)
    missing.to_csv(missing_path, index=False)

    print(f"\nSaved:")
    print(f"  {train_path} ({len(training)} rows)")
    print(f"  {pred_path} ({len(pred_samples)} rows)")
    print(f"  {missing_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

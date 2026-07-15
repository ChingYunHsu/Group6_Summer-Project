"""analytics_kpi_formulas.py — Sprint 4 KPI formula definitions (Data-owned).

Defines the computation formulas for the InsightsDashboard response fields.
Each function is pure: accepts DataFrames/values, returns dicts/values.
No DB connections, no HTTP — callable from backend or offline tests.

Formula version: 1.0.0 (Sprint 4 freeze candidate)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Ensure the parent stage directory (7.13-7.18) is importable so score_utils is reachable.
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORMULA_VERSION = "1.0.0"

# busyness_score 0-100 → level
BUSY_THRESHOLDS = {"quiet": (0, 29), "moderate": (30, 70), "busy": (71, 100)}

# District enum (frozen for Sprint 4)
DISTRICTS = ("midtown_east", "midtown_west", "uptown", "downtown")

# Travel window: look-ahead hours, window duration in hours
TRAVEL_WINDOW_LOOKAHEAD_H = 12
TRAVEL_WINDOW_DURATION_H = 1.5

# Availability penalty (minutes added to rank_score when venue is busy/diverting)
AVAILABILITY_PENALTY = {
    "quiet": 0,
    "moderate": 5,
    "busy": 15,
    "no_data": 10,
}

# Default travel time when transit source unavailable (minutes)
DEFAULT_TRAVEL_MINUTES = 15


# ---------------------------------------------------------------------------
# Helper: busyness_score → level
# ---------------------------------------------------------------------------

from score_utils import score_to_level


def busyness_to_level(score: float) -> str:
    """Map 0-100 score to quiet/moderate/busy/no_data.

    Delegates to score_utils.score_to_level (canonical implementation).
    Preserves the Sprint 3 boundary: 70 → moderate (not busy).
    """
    import numpy as np
    if score is None or (isinstance(score, float) and np.isnan(score)):
        return "no_data"
    s = float(score)
    # Maintain exact Sprint 3 boundary: 70 is moderate, not busy.
    # score_to_level uses (70, 101, "busy") which maps 70 → busy,
    # so handle 70 explicitly before delegating.
    if s == 70:
        return "moderate"
    return score_to_level(s)


# ---------------------------------------------------------------------------
# 1. Real-Time Density
# ---------------------------------------------------------------------------

def compute_real_time_density(
    latest_scores: pd.DataFrame,
    total_venues_in_district: int,
    previous_scores: Optional[pd.DataFrame] = None,
) -> dict:
    """Compute real-time density percent and trend.

    Args:
        latest_scores: DataFrame with columns [venue_id, score, level]
                       representing the most recent busyness snapshot per venue.
        total_venues_in_district: Total venues (any type) in the district.
        previous_scores: Same shape, for the previous hour. If None, trend is
                         computed from latest_scores alone (no trend available).

    Returns:
        {"percent": int 0-100, "trend": str, "trend_label": str}
    """
    total = max(total_venues_in_district, 1)
    active = len(latest_scores[latest_scores["level"].isin(("moderate", "busy"))])
    percent = round(active / total * 100)

    if previous_scores is not None and len(previous_scores) > 0:
        prev_active = len(previous_scores[previous_scores["level"].isin(("moderate", "busy"))])
        prev_percent = round(prev_active / total * 100)
        delta = percent - prev_percent
        sign = "+" if delta >= 0 else ""
        trend = f"{sign}{delta}% vs last hour"
    else:
        trend = "—"

    return {
        "percent": percent,
        "trend": trend,
        "trend_label": trend,
    }


# ---------------------------------------------------------------------------
# 2. Quick Triage Demand
# ---------------------------------------------------------------------------

def compute_quick_triage(
    venue_scores: pd.DataFrame,
    venues: pd.DataFrame,
) -> dict:
    """Find the venue with the lowest estimated wait in the district.

    Args:
        venue_scores: [venue_id, score, level, estimated_wait_minutes]
        venues: [venue_id, venue_name, district]

    Returns:
        {"wait_minutes": int, "label": str, "venue_name": str}
    """
    if venue_scores.empty:
        return {"wait_minutes": 0, "label": "No data", "venue_name": "No venues available"}

    merged = venue_scores.merge(venues[["venue_id", "name"]], on="venue_id", how="left")
    merged["name"] = merged["name"].fillna("Unknown Venue")

    # Prefer lowest estimated_wait; fallback to lowest score
    if "estimated_wait_minutes" in merged.columns and merged["estimated_wait_minutes"].notna().any():
        best = merged.loc[merged["estimated_wait_minutes"].idxmin()]
    else:
        best = merged.loc[merged["score"].idxmin()]

    return {
        "wait_minutes": int(best.get("estimated_wait_minutes", 0) or 0),
        "label": str(best["name"]),
        "venue_name": str(best["name"]),
    }


# ---------------------------------------------------------------------------
# 3. Best Travel Window
# ---------------------------------------------------------------------------

def compute_best_travel_window(
    forecast_curve: pd.DataFrame,
    start_hour: int = 0,
) -> dict:
    """Find the lowest-busyness 90-min window in the next 12h.

    Args:
        forecast_curve: [offset_hours (0-11), predicted_score]
        start_hour: hour of day for offset 0 (used to compute clock times)

    Returns:
        {"start_time": "HH:MM", "end_time": "HH:MM", "cta_label": str}
    """
    if forecast_curve.empty or len(forecast_curve) < 2:
        return {"start_time": "—", "end_time": "—", "cta_label": "No forecast available"}

    scores = forecast_curve.set_index("offset_hours")["predicted_score"]
    window_points = max(1, int(TRAVEL_WINDOW_DURATION_H))
    best_start = 0
    best_mean = float("inf")

    for i in range(len(scores) - window_points + 1):
        wmean = scores.iloc[i : i + window_points].mean()
        if wmean < best_mean:
            best_mean = wmean
            best_start = i

    start_h = (start_hour + best_start) % 24
    end_h = (start_hour + best_start + window_points) % 24

    return {
        "start_time": f"{start_h:02d}:00",
        "end_time": f"{end_h:02d}:00",
        "cta_label": "Plan Route",
    }


# ---------------------------------------------------------------------------
# 4. Regional Density Trends (7-day history)
# ---------------------------------------------------------------------------

def compute_regional_trends(
    daily_scores: pd.DataFrame,
    district: str,
) -> list[int]:
    """Compute 7-day history of average busyness for a district.

    Args:
        daily_scores: [date, district, avg_score] — one row per district per day.
        district: district slug to filter on.

    Returns:
        [int, ...] — 7 values, one per day (most recent last).
    """
    subset = daily_scores[daily_scores["district"] == district].copy()
    if subset.empty:
        return [0] * 7

    subset["date"] = pd.to_datetime(subset["date"])
    subset = subset.sort_values("date").tail(7)
    return [round(s) for s in subset["avg_score"].tolist()]


# ---------------------------------------------------------------------------
# 5. Fastest Hubs Leaderboard
# ---------------------------------------------------------------------------

def compute_fastest_hubs(
    venues: pd.DataFrame,
    venue_scores: pd.DataFrame,
    travel_times: Optional[pd.DataFrame] = None,
    top_n: int = 3,
) -> list[dict]:
    """Rank venues by composite cost: travel + wait + availability penalty.

    Args:
        venues: [venue_id, name, district, language_tags, accessible_status]
        venue_scores: [venue_id, score, level, estimated_wait_minutes]
        travel_times: [venue_id, travel_minutes] — optional, from MTA/Citi Bike
                      or cached. If omitted, DEFAULT_TRAVEL_MINUTES is used.
        top_n: number of hubs to return.

    Returns:
        [{rank, venue_id, venue_name, travel_minutes, wait_minutes,
          flow_status, language_flags}]
    """
    merged = venues[["venue_id", "name", "language_tags"]].merge(
        venue_scores[["venue_id", "score", "level", "estimated_wait_minutes"]],
        on="venue_id",
        how="inner",
    )

    if travel_times is not None and not travel_times.empty:
        merged = merged.merge(travel_times[["venue_id", "travel_minutes"]], on="venue_id", how="left")
    else:
        merged["travel_minutes"] = DEFAULT_TRAVEL_MINUTES

    merged["travel_minutes"] = merged["travel_minutes"].fillna(DEFAULT_TRAVEL_MINUTES)
    merged["estimated_wait_minutes"] = merged["estimated_wait_minutes"].fillna(10)
    merged["availability_penalty"] = merged["level"].map(AVAILABILITY_PENALTY).fillna(10)

    merged["rank_score"] = (
        merged["travel_minutes"].astype(float)
        + merged["estimated_wait_minutes"].astype(float)
        + merged["availability_penalty"].astype(float)
    )

    # Tie-break: lower wait, then lower travel, then alphabetical
    merged = merged.sort_values(
        ["rank_score", "estimated_wait_minutes", "travel_minutes", "name"],
        ascending=[True, True, True, True],
    )

    hubs = []
    for rank, (_, row) in enumerate(merged.head(top_n).iterrows(), start=1):
        flow = row["level"].upper() if row["level"] != "no_data" else "NO DATA"
        langs = row.get("language_tags")
        if isinstance(langs, str):
            import json
            langs = json.loads(langs)
        language_flags = list(langs) if isinstance(langs, list) else []

        hubs.append({
            "rank": rank,
            "venue_id": row["venue_id"],
            "venue_name": row["name"],
            "travel_minutes": int(row["travel_minutes"]),
            "wait_minutes": int(row["estimated_wait_minutes"]),
            "flow_status": flow,
            "language_flags": language_flags,
        })

    return hubs


# ---------------------------------------------------------------------------
# 6. Aggregate district dashboard (master function)
# ---------------------------------------------------------------------------

def aggregate_insights_dashboard(
    district: str,
    venues: pd.DataFrame,
    latest_scores: pd.DataFrame,
    previous_scores: Optional[pd.DataFrame],
    forecast_curve: pd.DataFrame,
    daily_scores: pd.DataFrame,
    travel_times: Optional[pd.DataFrame] = None,
    data_mode: str = "db",
) -> dict:
    """Assemble the full InsightsDashboard response from DB-backed data.

    Args:
        district: one of midtown_east, midtown_west, uptown, downtown.
        venues: all venues with [venue_id, name, district, language_tags].
        latest_scores: latest busyness snapshot per venue.
        previous_scores: previous hour snapshot.
        forecast_curve: district-level aggregate forecast (12 offsets).
        daily_scores: 7-day history [date, district, avg_score].
        travel_times: optional MTA/Citi Bike travel matrix.
        data_mode: "db" | "mock" | "partial" — marks data provenance.

    Returns:
        dict matching the InsightsDashboard OpenAPI schema.
    """
    district_venues = venues[venues["district"] == district]
    district_ids = set(district_venues["venue_id"])

    district_scores = latest_scores[latest_scores["venue_id"].isin(district_ids)]
    prev_scores = None
    if previous_scores is not None:
        prev_scores = previous_scores[previous_scores["venue_id"].isin(district_ids)]

    density = compute_real_time_density(district_scores, len(district_venues), prev_scores)
    triage = compute_quick_triage(district_scores, district_venues)
    travel_window = compute_best_travel_window(forecast_curve)
    trends = compute_regional_trends(daily_scores, district)
    hubs = compute_fastest_hubs(district_venues, district_scores, travel_times)

    prediction_series = [round(s) for s in forecast_curve["predicted_score"].tolist()] if not forecast_curve.empty else []

    return {
        "district": district,
        "real_time_density": density,
        "quick_triage": triage,
        "best_travel_window": travel_window,
        "chart_mode": "12_hour_predicted",
        "prediction_series": prediction_series,
        "history_series_7d": trends,
        "fastest_hubs": hubs,
        "formula_version": FORMULA_VERSION,
        "data_mode": data_mode,
    }

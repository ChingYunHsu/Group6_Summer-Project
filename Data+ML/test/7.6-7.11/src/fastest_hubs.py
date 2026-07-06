"""fastest_hubs.py — Sprint 4 D4.4 Fastest Hubs Leaderboard Cost Function (Data-owned).

Defines the composite rank score and tie-break rules for the Fastest Hubs
leaderboard in the Insights Dashboard.

Formula (frozen Sprint 4):
  rank_score = travel_minutes + estimated_wait_minutes + availability_penalty

Tie-break (deterministic, in order):
  1. Lower estimated_wait_minutes
  2. Lower travel_minutes
  3. Alphabetical by venue name

Formula version: 1.0.0 (Sprint 4 freeze)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

FORMULA_VERSION = "1.0.0"

# Availability penalty (minutes) added to rank_score per busyness level
AVAILABILITY_PENALTY = {
    "quiet": 0,
    "moderate": 5,
    "busy": 15,
    "no_data": 10,
}

# Default travel time when MTA/Citi Bike unavailable (minutes)
DEFAULT_TRAVEL_MINUTES = 15

# Default wait time when no estimate available (minutes)
DEFAULT_WAIT_MINUTES = 10

# Sources for travel times
TRAVEL_TIME_SOURCES = ("mta_live", "citibike_live", "cached", "static_fallback")

# Flow status labels (mapped from busyness level)
FLOW_STATUS_MAP = {
    "quiet": "OPTIMAL FLOW",
    "moderate": "MODERATE",
    "busy": "DIVERTING",
    "no_data": "NO DATA",
}


def compute_rank_score(
    travel_minutes: float,
    wait_minutes: float,
    busyness_level: str,
) -> float:
    """Composite cost function for ranking hubs.

    Args:
        travel_minutes: Transit time from user location (minutes).
        wait_minutes: Estimated wait time at venue (minutes).
        busyness_level: 'quiet' | 'moderate' | 'busy' | 'no_data'.

    Returns:
        rank_score (lower = better).
    """
    penalty = AVAILABILITY_PENALTY.get(busyness_level, 10)
    return travel_minutes + wait_minutes + penalty


def rank_hubs(
    venues: pd.DataFrame,
    venue_scores: pd.DataFrame,
    travel_times: Optional[pd.DataFrame] = None,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    top_n: int = 5,
) -> pd.DataFrame:
    """Rank venues by composite cost for the Fastest Hubs leaderboard.

    Args:
        venues: [venue_id, name, district, language_tags, accessible_status, latitude, longitude].
        venue_scores: [venue_id, score, level, estimated_wait_minutes].
        travel_times: [venue_id, travel_minutes, travel_time_source] or None.
        user_lat, user_lon: User coordinates (reserved for future distance calc).
        top_n: Max hubs to return.

    Returns:
        DataFrame sorted by rank_score ascending, with tie-breaks applied.
    """
    merged = venues[["venue_id", "name", "language_tags", "accessible_status"]].merge(
        venue_scores[["venue_id", "score", "level", "estimated_wait_minutes"]],
        on="venue_id",
        how="inner",
    )

    if travel_times is not None and not travel_times.empty:
        merged = merged.merge(
            travel_times[["venue_id", "travel_minutes", "travel_time_source"]],
            on="venue_id",
            how="left",
        )
        merged["travel_time_source"] = merged["travel_time_source"].fillna("static_fallback")
    else:
        merged["travel_minutes"] = DEFAULT_TRAVEL_MINUTES
        merged["travel_time_source"] = "static_fallback"

    merged["travel_minutes"] = merged["travel_minutes"].fillna(DEFAULT_TRAVEL_MINUTES)
    merged["estimated_wait_minutes"] = merged["estimated_wait_minutes"].fillna(DEFAULT_WAIT_MINUTES)
    merged["availability_penalty"] = merged["level"].map(AVAILABILITY_PENALTY).fillna(10)

    merged["rank_score"] = (
        merged["travel_minutes"].astype(float)
        + merged["estimated_wait_minutes"].astype(float)
        + merged["availability_penalty"].astype(float)
    )

    merged["flow_status"] = merged["level"].map(FLOW_STATUS_MAP).fillna("NO DATA")

    # Deterministic tie-break:
    #   1. Lower estimated_wait_minutes
    #   2. Lower travel_minutes
    #   3. Alphabetical by name
    merged = merged.sort_values(
        ["rank_score", "estimated_wait_minutes", "travel_minutes", "name"],
        ascending=[True, True, True, True],
    )

    merged["rank"] = range(1, len(merged) + 1)
    return merged.head(top_n)[[
        "rank", "venue_id", "name", "rank_score", "travel_minutes",
        "estimated_wait_minutes", "availability_penalty", "flow_status",
        "language_tags", "accessible_status", "travel_time_source",
    ]].reset_index(drop=True)


def leaderboard_response(hubs: pd.DataFrame) -> list[dict]:
    """Convert ranked hubs DataFrame to API response format."""
    import json

    result = []
    for _, row in hubs.iterrows():
        langs = row.get("language_tags")
        if isinstance(langs, str):
            langs = json.loads(langs)
        language_flags = list(langs) if isinstance(langs, list) else []

        result.append({
            "rank": int(row["rank"]),
            "venue_id": row["venue_id"],
            "venue_name": row["name"],
            "travel_minutes": int(row["travel_minutes"]),
            "wait_minutes": int(row["estimated_wait_minutes"]),
            "flow_status": row["flow_status"],
            "language_flags": language_flags,
            "travel_time_source": row.get("travel_time_source", "static_fallback"),
        })

    return result

"""Test fixtures for analytics KPI formulas — Sprint 4.

Provides fixed DataFrames that exercise each formula path:
- normal district with mixed busyness levels
- empty district (no_data)
- edge cases (all quiet, all busy, single venue)
"""

from __future__ import annotations

import pandas as pd


def fixture_venues() -> pd.DataFrame:
    """8 venues across 2 districts."""
    return pd.DataFrame([
        {"venue_id": "v_1001", "name": "Central Park Urgent Care", "district": "midtown_east",
         "venue_type": "healthcare", "language_tags": ["EN", "FR"], "accessible_status": "full_access"},
        {"venue_id": "v_1002", "name": "Brooklyn Bridge Pharmacy", "district": "midtown_east",
         "venue_type": "pharmacy", "language_tags": ["EN", "ES"], "accessible_status": "partial"},
        {"venue_id": "v_1003", "name": "Queens Transit Hub", "district": "midtown_east",
         "venue_type": "clinic", "language_tags": ["EN", "ZH"], "accessible_status": "step_free_route_only"},
        {"venue_id": "v_1004", "name": "East Side Dental", "district": "midtown_east",
         "venue_type": "dentist", "language_tags": ["EN"], "accessible_status": "none"},
        {"venue_id": "v_2001", "name": "Uptown Medical Center", "district": "uptown",
         "venue_type": "hospital", "language_tags": ["EN", "FR", "ES"], "accessible_status": "full_access"},
        {"venue_id": "v_2002", "name": "Harlem Pharmacy", "district": "uptown",
         "venue_type": "pharmacy", "language_tags": ["EN", "ES"], "accessible_status": "partial"},
        {"venue_id": "v_2003", "name": "Washington Heights Clinic", "district": "uptown",
         "venue_type": "clinic", "language_tags": ["EN", "ZH"], "accessible_status": "full_access"},
        {"venue_id": "v_2004", "name": "Inwood Restroom", "district": "uptown",
         "venue_type": "restroom", "language_tags": ["EN"], "accessible_status": "partial"},
    ])


def fixture_latest_scores() -> pd.DataFrame:
    """Current-hour busyness snapshot — mixed levels."""
    return pd.DataFrame([
        {"venue_id": "v_1001", "score": 45, "level": "moderate", "estimated_wait_minutes": 5},
        {"venue_id": "v_1002", "score": 85, "level": "busy", "estimated_wait_minutes": 20},
        {"venue_id": "v_1003", "score": 20, "level": "quiet", "estimated_wait_minutes": 2},
        {"venue_id": "v_1004", "score": 92, "level": "busy", "estimated_wait_minutes": 30},
        {"venue_id": "v_2001", "score": 55, "level": "moderate", "estimated_wait_minutes": 10},
        {"venue_id": "v_2002", "score": 10, "level": "quiet", "estimated_wait_minutes": 0},
        {"venue_id": "v_2003", "score": 75, "level": "busy", "estimated_wait_minutes": 15},
        {"venue_id": "v_2004", "score": None, "level": "no_data", "estimated_wait_minutes": None},
    ])


def fixture_previous_scores() -> pd.DataFrame:
    """Previous-hour snapshot for trend computation."""
    return pd.DataFrame([
        {"venue_id": "v_1001", "score": 40, "level": "moderate", "estimated_wait_minutes": 8},
        {"venue_id": "v_1002", "score": 70, "level": "moderate", "estimated_wait_minutes": 15},
        {"venue_id": "v_1003", "score": 15, "level": "quiet", "estimated_wait_minutes": 3},
        {"venue_id": "v_1004", "score": 90, "level": "busy", "estimated_wait_minutes": 25},
        {"venue_id": "v_2001", "score": 60, "level": "moderate", "estimated_wait_minutes": 12},
        {"venue_id": "v_2002", "score": 5, "level": "quiet", "estimated_wait_minutes": 1},
        {"venue_id": "v_2003", "score": 80, "level": "busy", "estimated_wait_minutes": 15},
        {"venue_id": "v_2004", "score": None, "level": "no_data", "estimated_wait_minutes": None},
    ])


def fixture_forecast_curve() -> pd.DataFrame:
    """12h aggregate district forecast — rising then falling."""
    return pd.DataFrame([
        {"offset_hours": i, "predicted_score": s}
        for i, s in enumerate([42, 38, 35, 33, 40, 52, 61, 68, 73, 64, 51, 39])
    ])


def fixture_daily_scores() -> pd.DataFrame:
    """7-day history for two districts."""
    dates = pd.date_range("2026-06-30", periods=7, freq="D")
    rows = []
    for i, d in enumerate(dates):
        rows.append({"date": d, "district": "midtown_east",
                      "avg_score": [58, 62, 49, 71, 66, 54, 47][i]})
        rows.append({"date": d, "district": "uptown",
                      "avg_score": [45, 48, 52, 55, 50, 47, 43][i]})
    return pd.DataFrame(rows)


def fixture_empty_scores() -> pd.DataFrame:
    """No scores available."""
    return pd.DataFrame(columns=["venue_id", "score", "level", "estimated_wait_minutes"])


def fixture_all_quiet_scores() -> pd.DataFrame:
    """All venues quiet."""
    return pd.DataFrame([
        {"venue_id": "v_1001", "score": 10, "level": "quiet", "estimated_wait_minutes": 0},
        {"venue_id": "v_1002", "score": 5, "level": "quiet", "estimated_wait_minutes": 0},
        {"venue_id": "v_1003", "score": 20, "level": "quiet", "estimated_wait_minutes": 3},
        {"venue_id": "v_1004", "score": 15, "level": "quiet", "estimated_wait_minutes": 1},
    ])

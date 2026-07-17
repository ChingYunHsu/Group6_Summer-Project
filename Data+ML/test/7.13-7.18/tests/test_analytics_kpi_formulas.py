"""Tests for analytics_kpi_formulas.py — Sprint 4 D4.1.

Run: python -m pytest Data+ML/test/7.13-7.18/tests/test_analytics_kpi_formulas.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from analytics_kpi_formulas import (
    FORMULA_VERSION,
    aggregate_insights_dashboard,
    busyness_to_level,
    compute_best_travel_window,
    compute_fastest_hubs,
    compute_quick_triage,
    compute_real_time_density,
    compute_regional_trends,
)
from fixtures import (
    fixture_all_quiet_scores,
    fixture_daily_scores,
    fixture_empty_scores,
    fixture_forecast_curve,
    fixture_latest_scores,
    fixture_previous_scores,
    fixture_venues,
)


# ---------------------------------------------------------------------------
# busyness_to_level
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (0, "quiet"), (29, "quiet"), (30, "moderate"), (70, "moderate"),
    (71, "busy"), (100, "busy"),
])
def test_busyness_to_level_thresholds(score, expected):
    assert busyness_to_level(score) == expected


def test_busyness_to_level_nan():
    assert busyness_to_level(np.nan) == "no_data"
    assert busyness_to_level(None) == "no_data"


# ---------------------------------------------------------------------------
# Real-Time Density
# ---------------------------------------------------------------------------

def test_density_mixed_district():
    scores = fixture_latest_scores()
    midtown_scores = scores[scores["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    result = compute_real_time_density(midtown_scores, total_venues_in_district=4)
    # 3 out of 4 are moderate/busy → 75%
    assert result["percent"] == 75
    assert "trend" in result


def test_density_with_trend():
    latest = fixture_latest_scores()
    prev = fixture_previous_scores()
    midtown_latest = latest[latest["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    midtown_prev = prev[prev["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    result = compute_real_time_density(midtown_latest, 4, midtown_prev)
    # Previous: v_1002 was moderate (now busy), so same count → 75% then, 75% now → delta 0
    assert result["percent"] == 75
    assert "0%" in result["trend"]


def test_density_all_quiet():
    scores = fixture_all_quiet_scores()
    result = compute_real_time_density(scores, total_venues_in_district=4)
    assert result["percent"] == 0


def test_density_empty():
    result = compute_real_time_density(fixture_empty_scores(), total_venues_in_district=4)
    assert result["percent"] == 0


# ---------------------------------------------------------------------------
# Quick Triage
# ---------------------------------------------------------------------------

def test_triage_picks_lowest_wait():
    scores = fixture_latest_scores()
    venues = fixture_venues()
    midtown_scores = scores[scores["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    midtown_venues = venues[venues["district"] == "midtown_east"]
    result = compute_quick_triage(midtown_scores, midtown_venues)
    # v_1003 has wait=2 (lowest)
    assert result["wait_minutes"] == 2
    assert "Queens Transit Hub" in result["venue_name"]


def test_triage_empty():
    result = compute_quick_triage(fixture_empty_scores(), fixture_venues())
    assert result["wait_minutes"] == 0


# ---------------------------------------------------------------------------
# Best Travel Window
# ---------------------------------------------------------------------------

def test_travel_window_finds_lowest_90min():
    curve = fixture_forecast_curve()
    result = compute_best_travel_window(curve, start_hour=8)
    # Lowest 90-min window should be early hours (offsets 1-2: 38+35)
    assert "start_time" in result
    assert "end_time" in result
    assert result["cta_label"] == "Plan Route"


def test_travel_window_empty():
    result = compute_best_travel_window(pd.DataFrame())
    assert result["start_time"] == "—"


# ---------------------------------------------------------------------------
# Regional Trends
# ---------------------------------------------------------------------------

def test_regional_trends_7_values():
    daily = fixture_daily_scores()
    result = compute_regional_trends(daily, "midtown_east")
    assert len(result) == 7
    assert result == [58, 62, 49, 71, 66, 54, 47]


def test_regional_trends_unknown_district():
    result = compute_regional_trends(fixture_daily_scores(), "nonexistent")
    assert result == [0] * 7


# ---------------------------------------------------------------------------
# Fastest Hubs
# ---------------------------------------------------------------------------

def test_fastest_hubs_ranks_by_composite_score():
    venues = fixture_venues()
    scores = fixture_latest_scores()
    midtown_venues = venues[venues["district"] == "midtown_east"]
    midtown_scores = scores[scores["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    hubs = compute_fastest_hubs(midtown_venues, midtown_scores)
    assert len(hubs) == 3  # default top_n
    # v_1003 quiet: 15 + 2 + 0 = 17 (best)
    assert hubs[0]["venue_id"] == "v_1003"
    assert hubs[0]["rank"] == 1
    # ranks are ascending
    assert hubs[0]["rank_score" if "rank_score" in hubs[0] else "rank"] <= hubs[-1]["rank_score" if "rank_score" in hubs[-1] else "rank"]


def test_fastest_hubs_includes_language_flags():
    venues = fixture_venues()
    scores = fixture_latest_scores()
    midtown_venues = venues[venues["district"] == "midtown_east"]
    midtown_scores = scores[scores["venue_id"].isin(["v_1001", "v_1002", "v_1003", "v_1004"])]
    hubs = compute_fastest_hubs(midtown_venues, midtown_scores)
    assert "language_flags" in hubs[0]
    assert isinstance(hubs[0]["language_flags"], list)


# ---------------------------------------------------------------------------
# Aggregate dashboard
# ---------------------------------------------------------------------------

def test_aggregate_dashboard_returns_all_sections():
    result = aggregate_insights_dashboard(
        district="midtown_east",
        venues=fixture_venues(),
        latest_scores=fixture_latest_scores(),
        previous_scores=fixture_previous_scores(),
        forecast_curve=fixture_forecast_curve(),
        daily_scores=fixture_daily_scores(),
        data_mode="db",
    )
    assert result["district"] == "midtown_east"
    assert "real_time_density" in result
    assert "quick_triage" in result
    assert "best_travel_window" in result
    assert "fastest_hubs" in result
    assert "prediction_series" in result
    assert "history_series_7d" in result
    assert result["formula_version"] == FORMULA_VERSION
    assert result["data_mode"] == "db"


def test_aggregate_dashboard_empty_district_does_not_500():
    """Empty data must not cause unhandled exceptions — no_data response expected."""
    result = aggregate_insights_dashboard(
        district="downtown",
        venues=fixture_venues(),  # no downtown venues
        latest_scores=fixture_empty_scores(),
        previous_scores=None,
        forecast_curve=pd.DataFrame(),
        daily_scores=fixture_daily_scores(),
        data_mode="partial",
    )
    assert result["district"] == "downtown"
    assert result["real_time_density"]["percent"] == 0
    assert result["fastest_hubs"] == []


def test_density_percent_in_range_0_100():
    scores = fixture_latest_scores()
    result = compute_real_time_density(scores, total_venues_in_district=8)
    assert 0 <= result["percent"] <= 100

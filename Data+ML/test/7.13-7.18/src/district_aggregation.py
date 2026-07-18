"""district_aggregation.py — Sprint 4 D4.3 District Aggregation Formulas (Data-owned).

Defines how district-level metrics are aggregated from venue-level data.
All formulas are deterministic, testable, and documented with inputs/weights/fallbacks.

Formula version: 1.0.0 (Sprint 4 freeze)
"""

from __future__ import annotations

import pandas as pd

FORMULA_VERSION = "1.0.0"
DISTRICTS = ("midtown_east", "midtown_west", "uptown", "downtown")

# Weights for district aggregation
DISTRICT_WEIGHTS = {
    "midtown_east": 1.0,
    "midtown_west": 1.0,
    "uptown": 0.9,
    "downtown": 0.9,
}


def aggregate_district_density(
    venue_scores: pd.DataFrame,
    district: str,
    total_venues: int,
) -> dict:
    """District live density: % of venues with moderate+ busyness.

    Formula: active_venues / total_venues * 100
    Input: latest busyness snapshot per venue in district.
    Fallback: if no scores, return 0 with no_data marker.
    """
    total = max(total_venues, 1)
    district_scores = venue_scores[venue_scores.get("district", pd.Series()) == district] if "district" in venue_scores.columns else venue_scores

    if district_scores.empty:
        return {"percent": 0, "data_mode": "no_data"}

    if "level" in district_scores.columns:
        active = len(district_scores[district_scores["level"].isin(("moderate", "busy"))])
    else:
        active = len(district_scores[district_scores["score"] > 30])

    return {
        "percent": round(active / total * 100),
        "data_mode": "live",
    }


def aggregate_district_trend(
    daily_history: pd.DataFrame,
    district: str,
    window_days: int = 7,
) -> dict:
    """7-day trend: average busyness per day, slope of last 7 days.

    Formula: mean of daily avg_scores over window, + slope direction.
    Input: [date, district, avg_score] per district per day.
    Fallback: if <2 days of data, return flat trend.
    """
    subset = daily_history[daily_history["district"] == district].copy()
    if len(subset) < 2:
        return {"trend": "flat", "values": [0] * window_days, "data_mode": "no_data"}

    subset["date"] = pd.to_datetime(subset["date"])
    subset = subset.sort_values("date").tail(window_days)
    values = [round(s) for s in subset["avg_score"].tolist()]

    # Simple slope: last value - first value
    delta = values[-1] - values[0]
    if delta > 5:
        trend = "rising"
    elif delta < -5:
        trend = "falling"
    else:
        trend = "flat"

    return {"trend": trend, "values": values, "data_mode": "live"}


def aggregate_district_forecast(
    forecast_curves: pd.DataFrame,
    district: str,
    district_venues: set[str],
) -> dict:
    """District-level 12h forecast: average of all venue forecasts in district.

    Formula: mean predicted_score per offset_hours across venues in district.
    Input: [venue_id, offset_hours, predicted_score] for all venues.
    Fallback: if no venues, return zeros.
    """
    if forecast_curves.empty or "venue_id" not in forecast_curves.columns:
        return {"prediction_series": [0] * 12, "data_mode": "no_data"}

    district_curves = forecast_curves[forecast_curves["venue_id"].isin(district_venues)]
    if district_curves.empty:
        return {"prediction_series": [0] * 12, "data_mode": "no_data"}

    agg = district_curves.groupby("offset_hours")["predicted_score"].mean()
    series = [round(agg.get(i, 0)) for i in range(12)]

    return {"prediction_series": series, "data_mode": "live"}


def compute_district_12h_low_window(
    forecast_series: list[int],
    window_hours: float = 1.5,
) -> dict:
    """Find lowest-busyness 90-min window in a district forecast series.

    Formula: sliding window of mean predicted_score, pick min.
    Input: 12-element list of predicted scores.
    Output: {start_offset, end_offset, start_time, end_time, mean_score}
    """
    if len(forecast_series) < 2:
        return {"start_offset": 0, "end_offset": 1, "mean_score": 0, "data_mode": "no_data"}

    window_points = max(1, int(window_hours))
    best_start = 0
    best_mean = float("inf")

    for i in range(len(forecast_series) - window_points + 1):
        wmean = sum(forecast_series[i : i + window_points]) / window_points
        if wmean < best_mean:
            best_mean = wmean
            best_start = i

    return {
        "start_offset": best_start,
        "end_offset": best_start + window_points,
        "start_time": f"{best_start:02d}:00",
        "end_time": f"{(best_start + window_points) % 24:02d}:00",
        "mean_score": round(best_mean, 1),
        "data_mode": "live",
    }

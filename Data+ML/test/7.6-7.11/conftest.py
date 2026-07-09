"""conftest.py — Shared fixtures for forecast-v2 tests.

Consolidates _make_venues / _make_scores / _make_reports that were inlined
in archive/test_forecast_v2_legacy.py (and duplicated _synth_* logic from the pipeline).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)


def make_venues(n: int = 5) -> pd.DataFrame:
    districts = ["Midtown", "Downtown", "Upper_East", "Upper_West", "Harlem", "Chelsea", "SoHo", "Financial_District"]
    hours_opts = [
        "9 AM–5 PM",
        "8 AM–8 PM",
        "Mo-Fr 08:00-18:00; Sa 09:00-14:00",
        "Open 24 hours",
        "8 AM–10 PM",
    ]
    return pd.DataFrame([
        {"venue_id": f"v_{1000 + i}", "name": f"Venue {i}",
         "venue_type": "clinic", "district": districts[i % len(districts)],
         "latitude": 40.75, "longitude": -73.98,
         "opening_hours": hours_opts[i % len(hours_opts)],
         "accessible_status": "full_access",
         "language_tags": '["EN"]', "primary_language": "EN",
         "rating": 4.0}
        for i in range(n)
    ])


def make_scores(venues: pd.DataFrame, hours_back: int = 48) -> pd.DataFrame:
    """Generate hourly scores. v_1001 gets no scores (fixture: no-live-score venue)."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = []
    for _, v in venues.iterrows():
        vid = v["venue_id"]
        if vid == "v_1001":
            continue  # no live data fixture
        start_h = 0 if vid != "v_1002" else hours_back // 2  # sparse fixture
        for h in range(start_h, hours_back):
            ts = now - timedelta(hours=h)
            score = RNG.uniform(20, 80)
            rows.append({
                "venue_id": vid, "score": round(score),
                "level": "moderate" if 30 <= score < 70 else ("quiet" if score < 30 else "busy"),
                "forecast_start_time": ts,
                "forecast_end_time": ts + timedelta(hours=12),
                "model_version": "nyc_traffic_baseline_v1",
                "created_at": ts,
            })
    return pd.DataFrame(rows).sort_values("forecast_start_time")


def make_reports(scores: pd.DataFrame) -> pd.DataFrame:
    """Generate reports for v_1003 only (fixture: venue-with-reports)."""
    times = sorted(scores[scores["venue_id"] == "v_1003"]["forecast_start_time"].unique())
    if len(times) < 5:
        return pd.DataFrame()
    return pd.DataFrame([
        {"report_id": f"r_test_{i}", "venue_id": "v_1003",
         "issue_type": "crowded", "status": "active",
         "created_at": times[-(i + 1)], "expires_at": times[-(i + 1)] + timedelta(hours=2)}
        for i in range(5)
    ])

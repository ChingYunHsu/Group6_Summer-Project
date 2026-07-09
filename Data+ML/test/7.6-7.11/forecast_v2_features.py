"""forecast_v2_features.py — Single source of truth for feature column lists.

All feature definitions live here. Both forecast_v2_feature_pipeline.py and
forecast_v2_model.py import from this module instead of maintaining their
own copies (saves ~60 lines of duplication per file).
"""

from __future__ import annotations

# ── Dynamic features (lookback-based) ─────────────────────────────────────────
DYNAMIC_FEATURES = [
    "latest_busyness_score", "latest_busyness_age_minutes", "latest_score_missing",
    "rolling_mean_1h", "rolling_mean_1h_missing",
    "rolling_mean_3h", "rolling_mean_3h_missing",
    "rolling_max_3h", "rolling_max_3h_missing",
    "recent_report_count_1h", "recent_report_count_1h_missing",
    "recent_report_count_3h", "recent_report_count_3h_missing",
    "active_report_severity_score", "active_report_severity_score_missing",
    "district_live_density", "district_live_density_missing",
    "venue_capacity_bucket",
]

# ── Time features (from target hour) ─────────────────────────────────────────
TIME_FEATURES = [
    "hour_of_day", "day_of_week", "day_of_week_index", "is_weekend",
    "is_business_hours", "time_bucket", "forecast_offset_hours",
    "target_hour_of_day", "target_day_of_week",
    "minutes_until_close", "minutes_since_open",
    "is_holiday_or_event_stub", "availability_penalty",
]

# ── Spatial features (venue-static, from MTA / Citi Bike files) ──────────────
SPATIAL_FEATURES = [
    "nearest_mta_distance_m", "nearest_citibike_distance_m",
]

# ── Traffic features (from busyness_scores × district × hour) ────────────────
TRAFFIC_FEATURES = [
    "district_traffic_score",
]

# ── Weather features ─────────────────────────────────────────────────────────
WEATHER_FEATURES = [
    "temperature_c", "temperature_missing",
    "humidity_pct", "humidity_missing",
    "wind_speed_kmh", "wind_missing",
    "precipitation_mm", "precipitation_missing",
    "weather_condition", "heat_alert", "heat_alert_missing",
    "weather_source",
]

# Holiday features — REMOVED 2026-07-08
# Rationale:
#   - venue_type distribution: emergencyasset 67.8% (24/7), healthcare 22.4% (mostly open),
#     restroom 9.8% (open). National holiday (Nager.Date) only affects a minority.
#   - is_major_event_nearby was being populated from Nager.Date (wrong data source:
#     national holidays ≠ local events like concerts/games). Should come from
#     Ticketmaster/eventbrite if reintroduced.
#   - opening_hours + is_business_hours + minutes_since_open already capture
#     "venue open at this moment" semantics more accurately per-venue.
# HOLIDAY_FEATURES = [
#     "is_public_holiday", "holiday_missing",
#     "is_major_event_nearby", "event_distance_km", "event_source",
# ]

# ── GBFS / Citi Bike features ────────────────────────────────────────────────
GBFS_FEATURES = [
    "citibike_station_activity", "citibike_activity_missing",
    "nearby_bike_availability", "nearby_dock_availability",
    "gbfs_source",
]

# ── MTA features ─────────────────────────────────────────────────────────────
MTA_FEATURES = [
    "mta_service_disruption_flag", "mta_disruption_missing",
    "mta_realtime_arrival_count_1h", "mta_arrival_missing",
    "mta_source",
]

# ── Categorical columns (for sklearn OneHotEncoder) ──────────────────────────
CATEGORICAL_FEATURES = [
    "day_of_week", "time_bucket",
    "weather_condition", "weather_source",
    "gbfs_source", "mta_source",
]

# ── Full feature matrix (all columns used by the model) ──────────────────────
ALL_FEATURES = (DYNAMIC_FEATURES + TIME_FEATURES + SPATIAL_FEATURES
                + TRAFFIC_FEATURES + WEATHER_FEATURES
                + GBFS_FEATURES + MTA_FEATURES)

# ── Production-pruned feature matrix (45 cols) ───────────────────────────────
# Generated 2026-07-08 by ML_V2.ipynb cell 10
# (Production Coverage Audit + Drop Decision on live-DB data).
#
# Differences from ALL_FEATURES (56 cols):
#   * 12 *_missing constant-flag columns dropped (all=0 or all=1 in production):
#       temperature_missing, humidity_missing, wind_missing, precipitation_missing,
#       heat_alert_missing, mta_disruption_missing, mta_arrival_missing,
#       citibike_activity_missing, active_report_severity_score_missing,
#       recent_report_count_1h_missing, recent_report_count_3h_missing,
#       (12th: holiday_missing — already removed with HOLIDAY_FEATURES)
#   * 3 *_missing real-signal columns KEPT (give model "lookback empty" signal):
#       latest_score_missing, rolling_mean_1h_missing, rolling_mean_3h_missing,
#       rolling_max_3h_missing, district_live_density_missing
#
# Caveats:
#   - active_report_severity_score_missing / recent_report_count_*_missing were
#     dropped only because the live user_reports table is currently empty
#     (no crowd reports yet ingested). When reports are populated, these
#     should be re-added (synthetic 7.2% rate, real signal).
#   - This list assumes weather/holiday/gbfs caches are populated by
#     external_feature_ingest.py. If caches empty, value columns also drop.
#   - Re-run cell 10 to regenerate if data sources change.
PRUNED_FEATURES_PRODUCTION = [
    # ── Dynamic (lookback) ── 15 cols
    "latest_busyness_score", "latest_busyness_age_minutes", "latest_score_missing",
    "rolling_mean_1h", "rolling_mean_1h_missing",
    "rolling_mean_3h", "rolling_mean_3h_missing",
    "rolling_max_3h", "rolling_max_3h_missing",
    "recent_report_count_1h", "recent_report_count_3h",
    "active_report_severity_score",
    "district_live_density", "district_live_density_missing",
    "venue_capacity_bucket",
    # ── Time ── 13 cols
    "hour_of_day", "day_of_week", "day_of_week_index", "is_weekend",
    "is_business_hours", "time_bucket", "forecast_offset_hours",
    "target_hour_of_day", "target_day_of_week",
    "minutes_until_close", "minutes_since_open",
    "is_holiday_or_event_stub", "availability_penalty",
    # ── Spatial ── 2 cols
    "nearest_mta_distance_m", "nearest_citibike_distance_m",
    # ── Traffic ── 1 col
    "district_traffic_score",
    # ── Weather (value cols only) ── 7 cols
    "temperature_c", "humidity_pct", "wind_speed_kmh", "precipitation_mm",
    "weather_condition", "heat_alert", "weather_source",
    # ── GBFS (value cols only) ── 4 cols
    "citibike_station_activity", "nearby_bike_availability",
    "nearby_dock_availability", "gbfs_source",
    # ── MTA (value cols only) ── 3 cols
    "mta_service_disruption_flag", "mta_realtime_arrival_count_1h", "mta_source",
]
# Sanity: PRUNED_FEATURES_PRODUCTION must be a strict subset of ALL_FEATURES.
# __all__ below prevents importing feature names that are not in the catalog.
assert set(PRUNED_FEATURES_PRODUCTION).issubset(set(ALL_FEATURES)), (
    f"PRUNED_FEATURES_PRODUCTION has features not in ALL_FEATURES: "
    f"{set(PRUNED_FEATURES_PRODUCTION) - set(ALL_FEATURES)}"
)
assert len(PRUNED_FEATURES_PRODUCTION) == 45, (
    f"PRUNED_FEATURES_PRODUCTION should have 45 cols, got {len(PRUNED_FEATURES_PRODUCTION)}"
)

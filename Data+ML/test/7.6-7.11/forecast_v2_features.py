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

# ── Holiday features ─────────────────────────────────────────────────────────
HOLIDAY_FEATURES = [
    "is_public_holiday", "holiday_missing",
    "is_major_event_nearby", "event_distance_km", "event_source",
]

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
    "event_source", "gbfs_source", "mta_source",
]

# ── Full feature matrix (all columns used by the model) ──────────────────────
ALL_FEATURES = (DYNAMIC_FEATURES + TIME_FEATURES + SPATIAL_FEATURES
                + TRAFFIC_FEATURES + WEATHER_FEATURES
                + HOLIDAY_FEATURES + GBFS_FEATURES + MTA_FEATURES)

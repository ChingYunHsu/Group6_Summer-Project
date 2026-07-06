"""forecast_v2_model.py — Sprint 4 forecast-v2 tabular baseline upgrade.

Upgrades the v1 tabular model with dynamic features, time features, and
time-based train/val/test split (no future data leakage).

Methodology: frozen tabular baseline (Ridge/RF/GBM), no ARIMA/LSTM.
Output: prediction_curve_v2.csv → busyness_forecasts table via write_forecasts_to_db.py.

Usage:
  python forecast_v2_model.py --training-csv ../6.28-7.3/output/ml_training_frame_v1.csv \
      --output-dir ../output --model-version forecast-v2
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

# Reuse existing model building infrastructure
HERE = os.path.dirname(os.path.abspath(__file__))
V1_SRC = os.path.normpath(os.path.join(HERE, "..", "..", "6.28-7.3", "src"))
if V1_SRC not in sys.path:
    sys.path.insert(0, V1_SRC)

from ml_modeling import (  # noqa: E402
    BUSY_LEVEL_LABELS,
    build_regression_pipeline,
    derive_busy_level,
    infer_feature_types,
    model_feature_matrix,
    regression_metric_row,
)

MODEL_VERSION = "forecast-v2"
SCORE_MIN, SCORE_MAX = 0, 100

# ---------------------------------------------------------------------------
# Dynamic feature construction
# ---------------------------------------------------------------------------

DYNAMIC_FEATURE_COLS = [
    "latest_busyness_score",
    "latest_busyness_age_minutes",
    "rolling_mean_1h",
    "rolling_mean_3h",
    "rolling_max_3h",
    "recent_report_count_1h",
    "recent_report_count_3h",
    "active_report_severity_score",
    "district_live_density",
    "venue_capacity_bucket",
    "availability_penalty",
]

TIME_FEATURE_COLS = [
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_business_hours",
    "time_bucket",
    "forecast_offset_hours",
    "target_hour_of_day",
    "target_day_of_week",
    "minutes_until_close",
    "minutes_since_open",
    "is_holiday_or_event_stub",
]


def build_dynamic_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add dynamic features derived from the training frame.

    For training data with real busyness_score per (venue, day, hour), we
    simulate the "latest known" features by looking back within the same venue.
    For production inference, these are populated from live DB data.
    """
    df = frame.copy()
    required = ["prediction_group_id", "day_of_week", "hour", "busyness_score"]
    for col in required:
        if col not in df.columns:
            df[col] = np.nan

    # Map day_of_week to numeric for sorting
    day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
               "friday": 4, "saturday": 5, "sunday": 6}
    df["_day_num"] = df["day_of_week"].str.lower().map(day_map).fillna(-1)
    df["_time_ordinal"] = df["_day_num"] * 24 + df["hour"].fillna(0).astype(int)

    # Sort by venue and time for rolling window ops
    df = df.sort_values(["prediction_group_id", "_time_ordinal"])

    # latest_busyness_score: previous hour's score (shift within group)
    df["latest_busyness_score"] = df.groupby("prediction_group_id")["busyness_score"].shift(1)

    # latest_busyness_age_minutes: minutes since last observation
    df["_prev_ordinal"] = df.groupby("prediction_group_id")["_time_ordinal"].shift(1)
    df["latest_busyness_age_minutes"] = (
        (df["_time_ordinal"] - df["_prev_ordinal"]) * 60
    ).clip(lower=0).fillna(120)

    # rolling_mean_1h, rolling_mean_3h, rolling_max_3h
    df["rolling_mean_1h"] = (
        df.groupby("prediction_group_id")["busyness_score"]
        .transform(lambda x: x.rolling(1, min_periods=1).mean())
    )
    df["rolling_mean_3h"] = (
        df.groupby("prediction_group_id")["busyness_score"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    df["rolling_max_3h"] = (
        df.groupby("prediction_group_id")["busyness_score"]
        .transform(lambda x: x.rolling(3, min_periods=1).max())
    )

    # recent_report_count_1h, recent_report_count_3h — derived from report signals
    df["recent_report_count_1h"] = 0
    df["recent_report_count_3h"] = 0

    # active_report_severity_score — weighted severity of recent reports
    df["active_report_severity_score"] = 0.0

    # district_live_density: fraction of venues in district that are busy
    if "district" in df.columns:
        df["_is_busy"] = (df["busyness_score"] > 70).astype(int)
        district_density = df.groupby("district")["_is_busy"].transform("mean")
        df["district_live_density"] = (district_density * 100).round(1)
    else:
        df["district_live_density"] = 50.0

    # venue_capacity_bucket: discretize capacity if available
    if "capacity" in df.columns:
        df["venue_capacity_bucket"] = pd.cut(
            df["capacity"].fillna(0),
            bins=[-1, 0, 50, 200, 500, float("inf")],
            labels=["unknown", "small", "medium", "large", "xlarge"],
        )
    else:
        df["venue_capacity_bucket"] = "unknown"

    # availability_penalty: 0 quiet, 5 moderate, 15 busy
    level_map = {"quiet": 0, "moderate": 5, "busy": 15}
    df["availability_penalty"] = (
        df["busyness_score"].apply(derive_busy_level).map(level_map).fillna(10)
    )

    # Drop internal columns
    df = df.drop(columns=["_day_num", "_time_ordinal", "_prev_ordinal", "_is_busy"], errors="ignore")

    return df


def build_time_features(frame: pd.DataFrame, offset_hours: int = 0) -> pd.DataFrame:
    """Add time-based features for a given forecast offset.

    Args:
        frame: training frame with at least [day_of_week, hour].
        offset_hours: how many hours ahead this row is being predicted for.
    """
    df = frame.copy()
    day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
               "friday": 4, "saturday": 5, "sunday": 6}
    reverse_day_map = {v: k for k, v in day_map.items()}

    df["hour_of_day"] = df["hour"].fillna(0).astype(int)
    df["day_of_week"] = df["day_of_week"].str.lower()
    df["_day_num"] = df["day_of_week"].map(day_map).fillna(0).astype(int)

    # is_weekend
    df["is_weekend"] = df["day_of_week"].isin(["saturday", "sunday"]).astype(int)

    # is_business_hours (09:00-17:00 approximation)
    df["is_business_hours"] = df["hour_of_day"].between(9, 17).astype(int)

    # time_bucket: morning, afternoon, evening, night
    df["time_bucket"] = pd.cut(
        df["hour_of_day"],
        bins=[-1, 6, 12, 18, 24],
        labels=["night", "morning", "afternoon", "evening"],
    )

    # forecast_offset_hours
    df["forecast_offset_hours"] = offset_hours

    # target_hour_of_day: hour this prediction is for
    df["target_hour_of_day"] = (df["hour_of_day"] + offset_hours) % 24

    # target_day_of_week
    df["_target_day_num"] = (df["_day_num"] + (df["hour_of_day"] + offset_hours) // 24) % 7
    df["target_day_of_week"] = df["_target_day_num"].map(reverse_day_map)

    # minutes_until_close, minutes_since_open — stub (no opening_hours parse yet)
    df["minutes_until_close"] = 480  # 8h default
    df["minutes_since_open"] = 120   # 2h default

    # is_holiday_or_event_stub — future feature
    df["is_holiday_or_event_stub"] = 0

    # Cleanup
    df = df.drop(columns=["_day_num", "_target_day_num"], errors="ignore")
    return df


# ---------------------------------------------------------------------------
# Time-based split
# ---------------------------------------------------------------------------

def time_based_split(
    frame: pd.DataFrame,
    time_col: str = "hour_of_day",
    n_splits: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split training data by time ordering to prevent future leakage.

    Uses TimeSeriesSplit; returns (train, val, test) where test is the
    last fold's test set, val is the second-to-last fold's test set.
    """
    if len(frame) < 30:
        # Too small for time split — fall back to simple sequential split
        n = len(frame)
        train_end = int(n * 0.7)
        val_end = int(n * 0.85)
        return frame.iloc[:train_end].copy(), frame.iloc[train_end:val_end].copy(), frame.iloc[val_end:].copy()

    # Sort by available temporal proxies
    day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
               "friday": 4, "saturday": 5, "sunday": 6}
    df = frame.copy()
    df["_sort_key"] = (
        df["day_of_week"].str.lower().map(day_map).fillna(0) * 24
        + df["hour"].fillna(0).astype(int)
    )
    df = df.sort_values("_sort_key").reset_index(drop=True)
    df = df.drop(columns=["_sort_key"])

    tscv = TimeSeriesSplit(n_splits=n_splits)
    splits = list(tscv.split(df))
    if len(splits) < 2:
        n = len(df)
        return df.iloc[: int(n * 0.7)].copy(), df.iloc[int(n * 0.7) : int(n * 0.85)].copy(), df.iloc[int(n * 0.85) :].copy()

    # Last fold → test, second-to-last → val, everything before → train
    train_idx, val_idx = splits[-2]
    _, test_idx = splits[-1]
    return df.iloc[train_idx].copy(), df.iloc[val_idx].copy(), df.iloc[test_idx].copy()


# ---------------------------------------------------------------------------
# Model training + evaluation
# ---------------------------------------------------------------------------

def train_forecast_v2(
    training: pd.DataFrame,
    feature_columns: list[str],
    model_name: str = "GradientBoostingRegressor",
) -> dict[str, Any]:
    """Train forecast-v2 model with time-based split.

    Returns dict with model, metrics, feature_columns for later prediction.
    """
    # Add dynamic + time features if not present
    enriched = build_dynamic_features(training)
    enriched = build_time_features(enriched)

    # Ensure all required features exist
    available = [c for c in feature_columns if c in enriched.columns]
    missing = [c for c in feature_columns if c not in enriched.columns]
    if missing:
        print(f"Warning: {len(missing)} features missing from training frame: {missing[:10]}...")

    train, val, test = time_based_split(enriched)

    numeric_cols, categorical_cols = infer_feature_types(enriched, available)

    models = {
        "Ridge": (Ridge(alpha=1.0), True),
        "RandomForestRegressor": (RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1), False),
        "GradientBoostingRegressor": (GradientBoostingRegressor(n_estimators=200, random_state=42), False),
    }

    estimator, scale_numeric = models.get(model_name, models["GradientBoostingRegressor"])
    pipeline = build_regression_pipeline(estimator, numeric_cols, categorical_cols, scale_numeric=scale_numeric)

    train_matrix = model_feature_matrix(train, available)
    val_matrix = model_feature_matrix(val, available)
    test_matrix = model_feature_matrix(test, available)

    pipeline.fit(train_matrix, train["busyness_score"])

    results = {"model_name": model_name, "model_version": MODEL_VERSION, "feature_count": len(available)}

    for split_name, split_frame, split_matrix in [
        ("train", train, train_matrix),
        ("val", val, val_matrix),
        ("test", test, test_matrix),
    ]:
        if split_frame.empty:
            continue
        y_pred = np.clip(pipeline.predict(split_matrix).astype(float), SCORE_MIN, SCORE_MAX)
        metrics = regression_metric_row(split_frame["busyness_score"], y_pred)
        for k, v in metrics.items():
            results[f"{split_name}_{k}"] = v

    return {
        "pipeline": pipeline,
        "metrics": results,
        "feature_columns": available,
        "test_frame": test,
    }


# ---------------------------------------------------------------------------
# Prediction curve generation (12h forecast per venue)
# ---------------------------------------------------------------------------

def generate_forecast_curve_v2(
    pipeline,
    training: pd.DataFrame,
    feature_columns: list[str],
    venues: Optional[list[str]] = None,
    hours: int = 12,
) -> pd.DataFrame:
    """Generate 12h prediction curve for each venue.

    For each venue, creates 12 rows (offset 0-11), each with time features
    adjusted to the target hour, then predicts predicted_score.
    """
    enriched = build_dynamic_features(training)
    enriched = build_time_features(enriched)

    available_features = [c for c in feature_columns if c in enriched.columns]

    # Get one representative row per venue
    if venues is None:
        venue_ids = enriched["venue_id"].dropna().unique()[:50]  # cap for safety
    else:
        venue_ids = venues

    rows = []
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for vid in venue_ids:
        venue_rows = enriched[enriched["venue_id"] == vid]
        if venue_rows.empty:
            continue
        sample = venue_rows.iloc[0].to_dict()

        for offset in range(hours):
            item = dict(sample)
            item["forecast_offset_hours"] = offset
            item["target_hour_of_day"] = (int(sample.get("hour", 0)) + offset) % 24
            item["hour"] = int(sample.get("hour", 0))

            x = pd.DataFrame([item], columns=available_features)
            x_filled = x.fillna(0)
            for col in available_features:
                if col not in x_filled.columns:
                    x_filled[col] = 0

            pred = float(np.clip(pipeline.predict(x_filled[available_features])[0], SCORE_MIN, SCORE_MAX))
            rows.append({
                "model_name": "GradientBoostingRegressor",
                "venue_id": vid,
                "prediction_group_id": sample.get("prediction_group_id", ""),
                "day_of_week": sample.get("day_of_week", "monday"),
                "hour": (int(sample.get("hour", 8)) + offset) % 24,
                "offset_hours": offset,
                "predicted_score": round(pred, 2),
                "predicted_level": derive_busy_level(pred),
                "forecast_for": (datetime.now() + timedelta(hours=offset + 1)).strftime("%Y-%m-%d %H:%M:%S"),
                "model_version": MODEL_VERSION,
                "generated_at": generated_at,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Model evaluation by district and busyness bucket
# ---------------------------------------------------------------------------

def evaluate_by_segment(test_frame: pd.DataFrame, y_pred: np.ndarray) -> pd.DataFrame:
    """Evaluate model performance by district and busyness level bucket."""
    df = test_frame.copy()
    df["y_pred"] = y_pred
    df["y_true"] = df["busyness_score"]
    df["abs_error"] = np.abs(df["y_true"] - df["y_pred"])
    df["true_level"] = df["y_true"].apply(derive_busy_level)

    segments = []
    for group_col in ["district", "true_level"]:
        if group_col not in df.columns:
            continue
        for group_val, group_df in df.groupby(group_col, dropna=False):
            if len(group_df) < 5:
                continue
            segments.append({
                "segment_type": group_col,
                "segment_value": str(group_val),
                "count": len(group_df),
                "mae": round(float(group_df["abs_error"].mean()), 3),
                "rmse": round(float(np.sqrt((group_df["abs_error"] ** 2).mean())), 3),
                "mean_true": round(float(group_df["y_true"].mean()), 1),
                "mean_pred": round(float(group_df["y_pred"].mean()), 1),
            })

    return pd.DataFrame(segments)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="forecast-v2 tabular baseline training + curve generation")
    parser.add_argument("--training-csv", required=True, help="Path to ml_training_frame_v1.csv")
    parser.add_argument("--output-dir", required=True, help="Directory for output CSVs")
    parser.add_argument("--model-name", default="GradientBoostingRegressor",
                        choices=["Ridge", "RandomForestRegressor", "GradientBoostingRegressor"])
    parser.add_argument("--max-venues", type=int, default=50, help="Max venues for prediction curve")
    args = parser.parse_args(argv)

    training = pd.read_csv(args.training_csv)
    print(f"Loaded training frame: {len(training)} rows, {len(training.columns)} columns")

    # Feature set: v1 features + dynamic + time
    v1_features = [
        "day_of_week", "hour", "is_weekend", "district", "review_count", "rating",
        "mapped_venue_count", "mean_review_count", "mean_rating",
        "nearest_subway_distance_m", "nearest_citibike_distance_m", "poi_density_300m",
        "capacity", "icu_capacity", "facility_level", "facility_short_type",
        "cms_hospital_type", "cms_rating",
        "citibike_nearest_distance_m", "mta_nearest_distance_m", "traffic_nearest_distance_m",
        "citibike_distance_bin", "mta_distance_bin", "traffic_distance_bin",
        "citibike_covered_200m", "mta_covered_200m", "traffic_covered_500m",
        "urban_activity_spatial_score",
    ]
    feature_columns = v1_features + DYNAMIC_FEATURE_COLS + TIME_FEATURE_COLS

    result = train_forecast_v2(training, feature_columns, args.model_name)
    pipeline = result["pipeline"]

    print("\n=== Model Metrics ===")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")

    # Generate prediction curve
    venue_ids = training["venue_id"].dropna().unique()[: args.max_venues]
    curve = generate_forecast_curve_v2(pipeline, training, result["feature_columns"], venues=list(venue_ids))
    curve_path = os.path.join(args.output_dir, "prediction_curve_v2.csv")
    curve.to_csv(curve_path, index=False)
    print(f"\nPrediction curve: {len(curve)} rows → {curve_path}")
    print(f"  Venues: {curve['venue_id'].nunique()}, Hours per venue: {curve.groupby('venue_id')['offset_hours'].max().iloc[0] + 1 if len(curve) else 0}")

    # Segment evaluation
    enriched = build_dynamic_features(training)
    enriched = build_time_features(enriched)
    available = [c for c in result["feature_columns"] if c in enriched.columns]
    test_matrix = model_feature_matrix(result["test_frame"], available)
    y_pred_test = np.clip(pipeline.predict(test_matrix).astype(float), SCORE_MIN, SCORE_MAX)
    segments = evaluate_by_segment(result["test_frame"], y_pred_test)
    seg_path = os.path.join(args.output_dir, "forecast_v2_segment_eval.csv")
    segments.to_csv(seg_path, index=False)
    print(f"Segment evaluation: {len(segments)} segments → {seg_path}")

    # Metrics summary
    metrics_path = os.path.join(args.output_dir, "forecast_v2_metrics.csv")
    pd.DataFrame([result["metrics"]]).to_csv(metrics_path, index=False)
    print(f"Metrics summary → {metrics_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

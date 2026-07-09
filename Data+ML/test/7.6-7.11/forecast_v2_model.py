"""forecast_v2_model.py — Train tabular regression models and generate prediction_curve_v2.csv.

Follows forecast-v2 SOP:
  - Time-based train/validation split (no random split)
  - Ridge, RandomForest, GradientBoosting baselines
  - Score clamped 0-100
  - Output prediction_curve_v2.csv with venue_id, forecast_for, offset_hours, etc.

Usage:
  python forecast_v2_model.py --features output/forecast_v2_training_features.csv --pred-features output/forecast_v2_prediction_features.csv
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from forecast_v2_features import (
    DYNAMIC_FEATURES, TIME_FEATURES, SPATIAL_FEATURES, TRAFFIC_FEATURES,
    WEATHER_FEATURES, GBFS_FEATURES, MTA_FEATURES,
    CATEGORICAL_FEATURES, ALL_FEATURES,
)
from score_utils import (
    BUSY_LEVEL_THRESHOLDS, clamp_score, score_to_level,
)

HERE = Path(__file__).resolve().parent


# ── Score utilities ── (imported from score_utils: score_to_level, clamp_score, BUSY_LEVEL_THRESHOLDS)


# ── Data preparation ──────────────────────────────────────────────────────────


def time_split(
    frame: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by forecast_for timestamp: earlier → train, later → val/test."""
    df = frame.sort_values("forecast_for").copy()
    n = len(df)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    return (
        df.iloc[:train_end].copy(),
        df.iloc[train_end:val_end].copy(),
        df.iloc[val_end:].copy(),
    )


def prepare_feature_matrix(frame: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Extract available feature columns; fill truly missing columns with sentinel."""
    available = [c for c in feature_cols if c in frame.columns]
    X = frame[available].copy()
    # Add missing columns as zeros with missing flag
    for c in feature_cols:
        if c not in frame.columns:
            X[c] = 0
    return X


def infer_column_types(frame: pd.DataFrame, feature_cols: list[str]) -> tuple[list[str], list[str]]:
    numeric, categorical = [], []
    for c in feature_cols:
        if c not in frame.columns:
            numeric.append(c)
        elif pd.api.types.is_numeric_dtype(frame[c]) or pd.api.types.is_bool_dtype(frame[c]):
            numeric.append(c)
        else:
            categorical.append(c)
    return numeric, categorical


# ── Model training ────────────────────────────────────────────────────────────


def build_pipeline(
    model: object,
    numeric_cols: list[str],
    categorical_cols: list[str],
    scale: bool = False,
) -> Pipeline:
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scaler", StandardScaler()))
    return Pipeline([
        ("preprocessor", ColumnTransformer([
            ("num", Pipeline(num_steps), numeric_cols),
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), categorical_cols),
        ], remainder="drop")),
        ("model", model),
    ])


MODEL_SPECS = {
    "Ridge": (Ridge(alpha=1.0), True),
    "RandomForestRegressor": (RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1), False),
    "GradientBoostingRegressor": (GradientBoostingRegressor(n_estimators=200, random_state=42), False),
}


def evaluate_model(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict[str, float]:
    clipped = np.clip(y_pred.astype(float), 0, 100)
    y_true_level = y_true.apply(score_to_level)
    y_pred_level = pd.Series(clipped).apply(score_to_level)
    return {
        "mae": round(float(mean_absolute_error(y_true, clipped)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, clipped))), 3),
        "r2": round(float(r2_score(y_true, clipped)), 3),
        "accuracy": round(float(accuracy_score(y_true_level, y_pred_level)), 3),
        "macro_f1": round(float(f1_score(y_true_level, y_pred_level, average="macro", zero_division=0)), 3),
    }


def evaluate_per_bucket(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    """MAE/RMSE per busyness bucket (low/medium/high)."""
    clipped = np.clip(y_pred.astype(float), 0, 100)
    y_true_level = y_true.apply(score_to_level)

    rows = []
    for bucket_label in ["quiet", "moderate", "busy"]:
        mask = y_true_level == bucket_label
        if mask.sum() == 0:
            continue
        rows.append({
            "bucket": bucket_label,
            "samples": int(mask.sum()),
            "mae": round(float(mean_absolute_error(y_true[mask], clipped[mask])), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true[mask], clipped[mask]))), 3),
        })
    return pd.DataFrame(rows)


# ── Main training run ─────────────────────────────────────────────────────────


def train_and_evaluate(
    training: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, dict[str, Pipeline], pd.DataFrame]:
    """Train all model specs, return (metrics, fitted_pipelines, test_predictions)."""
    train, val, test = time_split(training)
    print(f"Time split: train={len(train)}, val={len(val)}, test={len(test)}")
    print(f"  train range: {train['forecast_for'].min()} → {train['forecast_for'].max()}")
    print(f"  val   range: {val['forecast_for'].min()} → {val['forecast_for'].max()}")
    print(f"  test  range: {test['forecast_for'].min()} → {test['forecast_for'].max()}")

    num_cols, cat_cols = infer_column_types(training, feature_cols)
    print(f"  numeric features: {len(num_cols)}, categorical: {len(cat_cols)}")

    X_train = prepare_feature_matrix(train, feature_cols)
    X_val = prepare_feature_matrix(val, feature_cols)
    X_test = prepare_feature_matrix(test, feature_cols)
    y_train = train["label_score"]
    y_val = val["label_score"]
    y_test = test["label_score"]

    metrics_rows: list[dict[str, Any]] = []
    fitted: dict[str, Pipeline] = {}
    test_preds: list[pd.DataFrame] = []

    for model_name, (estimator, scale) in MODEL_SPECS.items():
        print(f"\n  Training {model_name}...")
        pipeline = build_pipeline(estimator, num_cols, cat_cols, scale=scale)
        pipeline.fit(X_train, y_train)
        fitted[model_name] = pipeline

        for split_name, y_split, X_split in [
            ("train", y_train, X_train),
            ("val", y_val, X_val),
            ("test", y_test, X_test),
        ]:
            if len(y_split) == 0:
                continue
            y_pred = pipeline.predict(X_split)
            base_metrics = evaluate_model(y_split, y_pred)
            metrics_rows.append({
                "model_name": model_name,
                "split": split_name,
                "feature_count": len(feature_cols),
                **base_metrics,
            })

        # Per-bucket evaluation on test
        if len(y_test) > 0:
            y_test_pred = pipeline.predict(X_test)
            bucket_metrics = evaluate_per_bucket(y_test, y_test_pred)
            for _, bm in bucket_metrics.iterrows():
                metrics_rows.append({
                    "model_name": model_name,
                    "split": f"test_{bm['bucket']}",
                    "feature_count": len(feature_cols),
                    "mae": bm["mae"],
                    "rmse": bm["rmse"],
                    "r2": float("nan"),
                    "accuracy": float("nan"),
                    "macro_f1": float("nan"),
                })

            # Store test predictions
            clipped = np.clip(y_test_pred.astype(float), 0, 100)
            pred_df = test[["venue_id", "forecast_for", "label_score"]].copy()
            pred_df["model_name"] = model_name
            pred_df["predicted_score"] = np.round(clipped, 2)
            pred_df["predicted_level"] = pd.Series(clipped).apply(score_to_level)
            pred_df["abs_error"] = np.round(np.abs(test["label_score"].to_numpy(dtype=float) - clipped), 2)
            test_preds.append(pred_df)

    return pd.DataFrame(metrics_rows), fitted, pd.concat(test_preds, ignore_index=True)


# ── Prediction curve generation ───────────────────────────────────────────────


def generate_prediction_curves(
    pipeline: Pipeline,
    pred_samples: pd.DataFrame,
    feature_cols: list[str],
    model_name: str,
) -> pd.DataFrame:
    """Generate a 12h forecast curve for every venue in pred_samples.

    Returns prediction_curve_v2.csv format: venue_id, forecast_for, offset_hours,
    predicted_score, predicted_level, model_version, generated_at.
    """
    X_pred = prepare_feature_matrix(pred_samples, feature_cols)
    y_pred = pipeline.predict(X_pred)
    clipped = np.clip(y_pred.astype(float), 0, 100)

    curve = pred_samples[["venue_id", "forecast_for", "offset_hours"]].copy()
    curve["predicted_score"] = np.round(clipped, 2)
    curve["predicted_level"] = pd.Series(clipped).apply(score_to_level)
    curve["model_version"] = "forecast-v2"
    curve["model_name"] = model_name
    curve["generated_at"] = datetime.now(timezone.utc).isoformat()

    return curve


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="forecast-v2 model training + prediction curve")
    p.add_argument("--features", type=Path, required=True,
                   help="Path to forecast_v2_training_features.csv")
    p.add_argument("--pred-features", type=Path, required=True,
                   help="Path to forecast_v2_prediction_features.csv")
    p.add_argument("--output-dir", type=Path, default=HERE / "output")
    p.add_argument("--model", choices=list(MODEL_SPECS), default="GradientBoostingRegressor",
                   help="Model to use for final prediction curve")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load
    print(f"Loading training features: {args.features}")
    training = pd.read_csv(args.features)
    print(f"  {len(training)} rows, {len(training.columns)} columns")

    print(f"\nLoading prediction features: {args.pred_features}")
    pred_samples = pd.read_csv(args.pred_features)
    print(f"  {len(pred_samples)} rows, {len(pred_samples.columns)} columns")

    # Find available features
    available = [c for c in ALL_FEATURES if c in training.columns]
    print(f"\nFeatures available: {len(available)}/{len(ALL_FEATURES)}")
    missing = [c for c in ALL_FEATURES if c not in training.columns]
    if missing:
        print(f"  Missing (will fill 0): {missing}")

    # Train
    metrics, fitted, test_preds = train_and_evaluate(training, available)

    # Save metrics
    metrics_path = args.output_dir / "forecast_v2_model_metrics.csv"
    metrics.to_csv(metrics_path, index=False)
    print(f"\nMetrics saved: {metrics_path}")
    print(metrics.to_string(index=False))

    # Save test predictions
    test_preds_path = args.output_dir / "forecast_v2_test_predictions.csv"
    test_preds.to_csv(test_preds_path, index=False)

    # Generate prediction curves
    best_model = fitted[args.model]
    print(f"\nGenerating prediction_curve_v2.csv using {args.model}...")
    curve = generate_prediction_curves(best_model, pred_samples, available, args.model)

    curve_path = args.output_dir / "prediction_curve_v2.csv"
    curve.to_csv(curve_path, index=False)
    print(f"  {curve_path} ({len(curve)} rows)")

    # Summarize
    n_venues = curve["venue_id"].nunique()
    offsets = curve.groupby("venue_id")["offset_hours"].max().value_counts().to_dict()
    print(f"\nPrediction curve summary:")
    print(f"  venues: {n_venues}")
    print(f"  offsets per venue: {offsets}")
    print(f"  score range: {curve['predicted_score'].min():.1f} - {curve['predicted_score'].max():.1f}")

    # level distribution
    level_dist = curve["predicted_level"].value_counts().to_dict()
    print(f"  levels: {level_dist}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BUSY_LEVEL_LABELS = ("quiet", "moderate", "busy")


def derive_busy_level(score: object) -> object:
    """将 busyness_score (0-100) 转为三档，与 ClearPath 前端一致：
    - 🟢 Green (Quiet):  < 30% capacity load
    - 🟡 Yellow (Moderate): 30%–70% capacity load
    - 🔴 Red (Busy): > 70% capacity load
    """
    if pd.isna(score):
        return pd.NA
    value = float(score)
    if value < 30:
        return "quiet"
    if value <= 70:
        return "moderate"
    return "busy"


def build_model_feature_blocks() -> dict[str, list[str]]:
    baseline = [
        "day_of_week",
        "hour",
        "is_weekend",
        "district",
        "review_count",
        "rating",
        "mapped_venue_count",
        "mean_review_count",
        "mean_rating",
    ]
    return {
        "baseline": baseline,
        "mobility": baseline + ["nearest_subway_distance_m", "nearest_citibike_distance_m"],
        "poi_density": baseline + ["poi_density_300m"],
        "capacity": baseline + [
            "nearest_subway_distance_m",
            "nearest_citibike_distance_m",
            "poi_density_300m",
            "capacity",
            "icu_capacity",
            "facility_level",
            "facility_short_type",
            "cms_hospital_type",
            "cms_rating",
        ],
        "urban_activity_spatial": baseline + [
            "citibike_nearest_distance_m",
            "mta_nearest_distance_m",
            "traffic_nearest_distance_m",
            "citibike_distance_bin",
            "mta_distance_bin",
            "traffic_distance_bin",
            "citibike_covered_200m",
            "mta_covered_200m",
            "traffic_covered_500m",
            "urban_activity_spatial_score",
        ],
        "full_available": baseline + [
            "nearest_subway_distance_m",
            "nearest_citibike_distance_m",
            "poi_density_300m",
            "capacity",
            "icu_capacity",
            "facility_level",
            "facility_short_type",
            "cms_hospital_type",
            "cms_rating",
            "citibike_nearest_distance_m",
            "mta_nearest_distance_m",
            "traffic_nearest_distance_m",
            "citibike_distance_bin",
            "mta_distance_bin",
            "traffic_distance_bin",
            "citibike_covered_200m",
            "mta_covered_200m",
            "traffic_covered_500m",
            "urban_activity_spatial_score",
        ],
    }


def split_training_frame(training: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        training[training["split"].eq("train")].copy(),
        training[training["split"].eq("val")].copy(),
        training[training["split"].eq("test")].copy(),
    )


def infer_feature_types(frame: pd.DataFrame, feature_columns: list[str]) -> tuple[list[str], list[str]]:
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    for column in feature_columns:
        if pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            numeric_columns.append(column)
        else:
            categorical_columns.append(column)
    return numeric_columns, categorical_columns


def model_feature_matrix(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    return frame[feature_columns].copy().where(pd.notna(frame[feature_columns]), np.nan)


def build_regression_pipeline(
    model: object,
    numeric_columns: list[str],
    categorical_columns: list[str],
    scale_numeric: bool = False,
) -> Pipeline:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    return Pipeline(
        [
            (
                "preprocessor",
                ColumnTransformer(
                    transformers=[
                        ("num", Pipeline(numeric_steps), numeric_columns),
                        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical_columns),
                    ],
                    remainder="drop",
                ),
            ),
            ("model", model),
        ]
    )


def regression_metric_row(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    clipped = np.clip(y_pred.astype(float), 0, 100)
    y_true_level = y_true.map(derive_busy_level)
    y_pred_level = pd.Series(clipped).map(derive_busy_level)
    return {
        "mae": round(float(mean_absolute_error(y_true, clipped)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, clipped))), 3),
        "r2": round(float(r2_score(y_true, clipped)), 3),
        "busy_level_accuracy": round(float(accuracy_score(y_true_level, y_pred_level)), 3),
        "macro_f1": round(float(f1_score(y_true_level, y_pred_level, average="macro", zero_division=0)), 3),
        "busy_recall": round(float(recall_score(y_true_level, y_pred_level, labels=["busy"], average="macro", zero_division=0)), 3),
    }


def build_model_specs() -> dict[str, tuple[object, bool]]:
    return {
        "Ridge": (Ridge(alpha=1.0), True),
        "RandomForestRegressor": (RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1), False),
        "GradientBoostingRegressor": (GradientBoostingRegressor(random_state=42), False),
    }


def select_representative_row(frame: pd.DataFrame) -> pd.Series:
    candidate = frame.dropna(subset=["venue_id"]).copy()
    if candidate.empty:
        return frame.iloc[0]
    sort_columns = [column for column in ["mapped_venue_count", "review_count", "rating", "mean_rating"] if column in candidate.columns]
    if not sort_columns:
        return candidate.iloc[0]
    return candidate.sort_values(sort_columns, ascending=[False] * len(sort_columns)).iloc[0]


def score_curve_sample(
    model_pipeline: Pipeline,
    sample: pd.Series,
    training_columns: list[str],
    feature_columns: list[str],
    hours: int = 12,
    start_hour: int = 8,
) -> tuple[int, float]:
    predictions: list[float] = []
    levels: list[str] = []
    for hour in range(start_hour, start_hour + hours):
        item = sample.to_dict()
        item["hour"] = hour % 24
        item["is_weekend"] = bool(item.get("day_of_week") in {"saturday", "sunday"})
        x = pd.DataFrame([item], columns=training_columns)
        prediction = float(np.clip(model_pipeline.predict(model_feature_matrix(x, feature_columns))[0], 0, 100))
        predictions.append(prediction)
        levels.append(derive_busy_level(prediction))
    return len(set(levels)), max(predictions) - min(predictions)


def select_curve_row(
    frame: pd.DataFrame,
    model_pipeline: Pipeline,
    feature_columns: list[str],
    hours: int = 12,
    start_hour: int = 8,
) -> pd.Series:
    candidates = (
        frame.dropna(subset=["venue_id"])
        .drop_duplicates(subset=["prediction_group_id", "venue_id", "day_of_week"])
        .copy()
    )
    if candidates.empty:
        return select_representative_row(frame)
    candidates["_level_count"], candidates["_score_range"] = zip(
        *candidates.apply(
            lambda row: score_curve_sample(model_pipeline, row, frame.columns.tolist(), feature_columns, hours, start_hour),
            axis=1,
        )
    )
    return candidates.sort_values(["_level_count", "_score_range"], ascending=[False, False]).iloc[0]


def build_prediction_curve(
    model_pipeline: Pipeline,
    training: pd.DataFrame,
    feature_columns: list[str],
    model_name: str,
    sample: pd.Series | None = None,
    hours: int = 12,
    start_hour: int = 8,
) -> pd.DataFrame:
    if sample is None:
        sample = select_representative_row(training[training["split"].eq("test")])
    rows: list[dict[str, Any]] = []
    for hour in range(start_hour, start_hour + hours):
        item = sample.to_dict()
        item["hour"] = hour % 24
        item["is_weekend"] = bool(item.get("day_of_week") in {"saturday", "sunday"})
        x = pd.DataFrame([item], columns=training.columns)
        prediction = float(np.clip(model_pipeline.predict(model_feature_matrix(x, feature_columns))[0], 0, 100))
        rows.append(
            {
                "model_name": model_name,
                "venue_id": item.get("venue_id"),
                "prediction_group_id": item.get("prediction_group_id"),
                "day_of_week": item.get("day_of_week"),
                "hour": int(item["hour"]),
                "predicted_score": round(prediction, 2),
                "predicted_level": derive_busy_level(prediction),
            }
        )
    return pd.DataFrame(rows)


def evaluate_model_family(
    training: pd.DataFrame,
    feature_columns: list[str],
    family_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, val, test = split_training_frame(training)
    available_features = [column for column in feature_columns if column in training.columns]
    numeric_columns, categorical_columns = infer_feature_types(training, available_features)
    train_matrix = model_feature_matrix(train, available_features)
    val_matrix = model_feature_matrix(val, available_features)
    test_matrix = model_feature_matrix(test, available_features)

    model_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    fitted_pipelines: dict[str, Pipeline] = {}
    for model_name, (estimator, scale_numeric) in build_model_specs().items():
        pipeline = build_regression_pipeline(estimator, numeric_columns, categorical_columns, scale_numeric=scale_numeric)
        pipeline.fit(train_matrix, train["busyness_score"])
        fitted_pipelines[model_name] = pipeline
        for split_name, split_frame, split_matrix in [
            ("train", train, train_matrix),
            ("val", val, val_matrix),
            ("test", test, test_matrix),
        ]:
            if split_frame.empty:
                continue
            clipped = np.clip(pipeline.predict(split_matrix).astype(float), 0, 100)
            model_rows.append(
                {
                    "family_name": family_name,
                    "model_name": model_name,
                    "split": split_name,
                    "feature_set": ",".join(available_features),
                    "feature_count": len(available_features),
                    **regression_metric_row(split_frame["busyness_score"], clipped),
                }
            )
            if split_name == "test":
                pred_frame = split_frame[[
                    "source_file",
                    "prediction_group_id",
                    "venue_id",
                    "place_title",
                    "day_of_week",
                    "hour",
                    "busyness_score",
                    "is_business_hours",
                    "hours_status",
                ]].copy()
                pred_frame["model_name"] = model_name
                pred_frame["predicted_score"] = np.round(clipped, 2)
                pred_frame["predicted_level"] = pd.Series(clipped).map(derive_busy_level).to_numpy()
                pred_frame["serving_predicted_level"] = np.where(
                    split_frame["is_business_hours"].fillna(False).astype(bool),
                    pred_frame["predicted_level"],
                    "no_data",
                )
                pred_frame["abs_error"] = np.round(np.abs(split_frame["busyness_score"].to_numpy(dtype=float) - clipped), 2)
                prediction_rows.append(pred_frame)
    selector = fitted_pipelines.get("GradientBoostingRegressor", next(iter(fitted_pipelines.values())))
    curve_sample = select_curve_row(test, selector, available_features)
    curve_rows = [
        build_prediction_curve(pipeline, training, available_features, model_name, sample=curve_sample)
        for model_name, pipeline in fitted_pipelines.items()
    ]
    return pd.DataFrame(model_rows), pd.concat(prediction_rows, ignore_index=True), pd.concat(curve_rows, ignore_index=True)


def build_ablation_summary(training: pd.DataFrame) -> pd.DataFrame:
    blocks = build_model_feature_blocks()
    train, _, test = split_training_frame(training)
    rows: list[dict[str, Any]] = []
    for block_name in ["baseline", "mobility", "poi_density", "capacity", "urban_activity_spatial", "full_available"]:
        feature_columns = blocks[block_name]
        missing_columns = [column for column in feature_columns if column not in training.columns]
        if missing_columns:
            rows.append(
                {
                    "block_name": block_name,
                    "status": "missing_source",
                    "model_name": "Ridge",
                    "feature_count": len(feature_columns) - len(missing_columns),
                    "missing_columns": ",".join(missing_columns),
                }
            )
            continue
        numeric_columns, categorical_columns = infer_feature_types(training, feature_columns)
        pipeline = build_regression_pipeline(Ridge(alpha=1.0), numeric_columns, categorical_columns, scale_numeric=True)
        pipeline.fit(model_feature_matrix(train, feature_columns), train["busyness_score"])
        clipped = np.clip(pipeline.predict(model_feature_matrix(test, feature_columns)).astype(float), 0, 100)
        rows.append(
            {
                "block_name": block_name,
                "status": "ok",
                "model_name": "Ridge",
                "feature_count": len(feature_columns),
                **regression_metric_row(test["busyness_score"], clipped),
            }
        )
    return pd.DataFrame(rows)


def imputed_feature_profile(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total_rows = len(frame)
    for column in feature_columns:
        if column not in frame.columns:
            rows.append(
                {
                    "feature": column,
                    "status": "missing_column",
                    "dtype": "missing",
                    "non_null_rows": 0,
                    "total_rows": total_rows,
                    "coverage_pct": 0.0,
                    "impute_strategy": pd.NA,
                    "impute_value": pd.NA,
                    "post_impute_unique_values": 0,
                    "post_impute_top_value_pct": 0.0,
                }
            )
            continue

        series = frame[column]
        non_null = int(series.notna().sum())
        is_numeric = pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series)
        strategy = "median" if is_numeric else "most_frequent"
        value = series.median() if is_numeric else (series.mode(dropna=True).iloc[0] if non_null else pd.NA)
        filled = series.fillna(value)
        top_pct = float(filled.value_counts(dropna=False, normalize=True).iloc[0] * 100) if len(filled) else 0.0
        rows.append(
            {
                "feature": column,
                "status": "ok" if non_null else "all_null",
                "dtype": "numeric" if is_numeric else "categorical",
                "non_null_rows": non_null,
                "total_rows": total_rows,
                "coverage_pct": round(non_null / total_rows * 100, 1) if total_rows else 0.0,
                "impute_strategy": strategy,
                "impute_value": value,
                "post_impute_unique_values": int(filled.nunique(dropna=False)),
                "post_impute_top_value_pct": round(top_pct, 1),
            }
        )
    return pd.DataFrame(rows)


def build_low_coverage_imputation_diagnostics(training: pd.DataFrame) -> pd.DataFrame:
    features = ["rating", "opening_hours", "capacity", "icu_capacity", "facility_level", "facility_short_type", "cms_hospital_type", "cms_rating"]
    return imputed_feature_profile(training, features)


def evaluate_ridge_feature_set(training: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    train, _, test = split_training_frame(training)
    available_features = [column for column in feature_columns if column in training.columns]
    numeric_columns, categorical_columns = infer_feature_types(training, available_features)
    pipeline = build_regression_pipeline(Ridge(alpha=1.0), numeric_columns, categorical_columns, scale_numeric=True)
    pipeline.fit(model_feature_matrix(train, available_features), train["busyness_score"])
    clipped = np.clip(pipeline.predict(model_feature_matrix(test, available_features)).astype(float), 0, 100)
    return {"feature_count": len(available_features), **regression_metric_row(test["busyness_score"], clipped)}


def build_low_coverage_drop_one_ablation(training: pd.DataFrame) -> pd.DataFrame:
    blocks = build_model_feature_blocks()
    capacity_features = blocks["capacity"]
    drop_candidates = ["rating", "opening_hours", "capacity", "icu_capacity", "facility_level", "facility_short_type", "cms_hospital_type", "cms_rating"]
    baseline_metrics = evaluate_ridge_feature_set(training, capacity_features)
    rows = [
        {
            "experiment": "capacity_block",
            "dropped_feature": "none",
            "status": "ok",
            **baseline_metrics,
            "delta_mae_vs_capacity_block": 0.0,
            "delta_r2_vs_capacity_block": 0.0,
        }
    ]
    for feature in drop_candidates:
        if feature not in capacity_features:
            continue
        reduced = [column for column in capacity_features if column != feature]
        metrics = evaluate_ridge_feature_set(training, reduced)
        rows.append(
            {
                "experiment": "drop_one_from_capacity_block",
                "dropped_feature": feature,
                "status": "ok",
                **metrics,
                "delta_mae_vs_capacity_block": round(metrics["mae"] - baseline_metrics["mae"], 3),
                "delta_r2_vs_capacity_block": round(metrics["r2"] - baseline_metrics["r2"], 3),
            }
        )
    return pd.DataFrame(rows)

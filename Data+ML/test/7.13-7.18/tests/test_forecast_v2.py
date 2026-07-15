"""Offline contracts for the canonical top-level forecast-v2 pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import forecast_v2_feature_pipeline as fp
import forecast_v2_model as model
from forecast_v2_quality_gate import gate_curve, gate_target_leakage, gate_train_val_split
from forecast_v2_writer import dry_run_sql, load_curve


def _frames():
    venues, scores, reports = fp.build_synthetic_data(n_venues=6, hours_back=72, seed=7)
    return (
        fp.build_training_samples(scores, venues, reports),
        fp.build_prediction_samples(venues, scores, reports),
    )


def test_time_split_has_no_overlapping_rows():
    training, _ = _frames()
    train, val, test = model.time_split(training)
    assert len(train) + len(val) + len(test) == len(training)
    assert train["forecast_for"].max() <= val["forecast_for"].min()
    assert val["forecast_for"].max() <= test["forecast_for"].min()


def test_training_produces_metrics_and_prediction_curve():
    training, prediction = _frames()
    features = [column for column in model.ALL_FEATURES if column in training.columns]
    metrics, fitted, test_predictions = model.train_and_evaluate(training, features)
    assert {"Ridge", "RandomForestRegressor", "GradientBoostingRegressor"} == set(fitted)
    assert {"mae", "rmse", "r2", "accuracy", "macro_f1"}.issubset(metrics.columns)
    assert {"label_score", "predicted_score", "model_name", "abs_error"}.issubset(test_predictions.columns)
    curve = model.generate_prediction_curves(
        fitted["GradientBoostingRegressor"], prediction, features, "GradientBoostingRegressor"
    )
    assert set(curve["model_version"]) == {"forecast-v2"}
    assert curve["predicted_score"].between(0, 100).all()
    assert curve.groupby("venue_id")["offset_hours"].nunique().eq(12).all()


def test_quality_gates_detect_expected_contracts():
    training, _ = _frames()
    findings, blocked = gate_train_val_split(training.to_dict("records"))
    assert not blocked
    assert any("duplicate gate" in finding for finding in findings)
    _, blocked = gate_target_leakage(list(training.columns))
    assert not blocked
    rows = [{"venue_id": "v1", "offset_hours": index} for index in range(12)]
    _, blocked = gate_curve(rows)
    assert not blocked


def test_writer_dry_run_accepts_canonical_curve(tmp_path):
    curve = pd.DataFrame([{
        "venue_id": "v_0001", "forecast_for": "2026-07-15T12:00:00+00:00",
        "offset_hours": 0, "predicted_score": 42.0, "predicted_level": "moderate",
        "model_version": "forecast-v2",
    }])
    path = tmp_path / "prediction_curve_v2.csv"
    curve.to_csv(path, index=False)
    row = load_curve(path)[0]
    sql = dry_run_sql(row["venue_id"], datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
                      row["predicted_score"], row["predicted_level"], "forecast-v2")
    assert "busyness_forecasts" in sql
    assert "forecast-v2" in sql

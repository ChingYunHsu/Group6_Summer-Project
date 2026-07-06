"""SOP 8 — pure-function tests for ml_modeling (offline, no DB / no live APIs).

Covers:
  * derive_busy_level() — 0-100 → quiet/moderate/busy thresholds + NA
  * regression_metric_row() — smoke: required metric fields present + clipped
  * build_prediction_curve() — 12-row output schema + score bounds + level legal
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import ml_modeling as mm


# ---------------------------------------------------------------------------
# derive_busy_level
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (0, "quiet"),
    (29, "quiet"),
    (29.9, "quiet"),
    (30, "moderate"),   # boundary: 30 is moderate (<=70)
    (50, "moderate"),
    (70, "moderate"),   # boundary: 70 is moderate (<=70)
    (70.01, "busy"),
    (71, "busy"),
    (100, "busy"),
])
def test_derive_busy_level_thresholds(score, expected):
    assert mm.derive_busy_level(score) == expected


def test_derive_busy_level_na_returns_na():
    assert pd.isna(mm.derive_busy_level(np.nan))
    assert pd.isna(mm.derive_busy_level(None))


def test_derive_busy_level_string_numeric_coerces():
    # float() coercion: "45" → 45.0 → moderate
    assert mm.derive_busy_level("45") == "moderate"


# ---------------------------------------------------------------------------
# regression_metric_row smoke
# ---------------------------------------------------------------------------

REQUIRED_METRIC_FIELDS = {"mae", "rmse", "r2", "busy_level_accuracy"}


def test_regression_metric_row_has_required_fields():
    y_true = pd.Series([10, 40, 80])
    y_pred = np.array([12, 38, 82])
    row = mm.regression_metric_row(y_true, y_pred)

    assert REQUIRED_METRIC_FIELDS.issubset(row.keys())
    for field in REQUIRED_METRIC_FIELDS:
        assert isinstance(row[field], (int, float))


def test_regression_metric_row_clips_predictions_to_0_100():
    # Predictions above 100 must be clipped before scoring (no NaN/error).
    y_true = pd.Series([20, 50])
    y_pred = np.array([150.0, -10.0])  # out of range
    row = mm.regression_metric_row(y_true, y_pred)
    # mae should reflect clipped [100, 0] vs [20, 50] → (80 + 50)/2 = 65
    assert row["mae"] == 65.0


def test_regression_metric_row_perfect_prediction():
    y_true = pd.Series([10, 40, 80])
    y_pred = np.array([10.0, 40.0, 80.0])
    row = mm.regression_metric_row(y_true, y_pred)
    assert row["mae"] == 0.0
    assert row["rmse"] == 0.0
    assert row["r2"] == 1.0
    assert row["busy_level_accuracy"] == 1.0


# ---------------------------------------------------------------------------
# build_prediction_curve
# ---------------------------------------------------------------------------

class _StubPipeline:
    """Minimal sklearn-Pipeline stand-in returning a constant prediction."""

    def __init__(self, value: float = 42.0):
        self._value = value

    def predict(self, X):
        return np.array([self._value] * len(X))


def _make_training_frame() -> pd.DataFrame:
    return pd.DataFrame([{
        "venue_id": "v_test",
        "prediction_group_id": "grp_1",
        "day_of_week": "monday",
        "hour": 8,
        "is_weekend": False,
        "split": "test",
        "busyness_score": 40,
    }])


def test_build_prediction_curve_emits_12_rows_with_contract_fields():
    training = _make_training_frame()
    curve = mm.build_prediction_curve(
        model_pipeline=_StubPipeline(42.0),
        training=training,
        feature_columns=["hour", "is_weekend"],
        model_name="Ridge",
        sample=training.iloc[0],
        hours=12,
        start_hour=8,
    )

    assert len(curve) == 12
    expected_cols = {
        "model_name", "venue_id", "prediction_group_id", "day_of_week",
        "hour", "predicted_score", "predicted_level",
    }
    assert expected_cols.issubset(set(curve.columns))


def test_build_prediction_curve_hours_span_start_to_start_plus_12():
    training = _make_training_frame()
    curve = mm.build_prediction_curve(
        model_pipeline=_StubPipeline(50.0),
        training=training,
        feature_columns=["hour"],
        model_name="Ridge",
        sample=training.iloc[0],
        hours=12,
        start_hour=8,
    )
    assert curve["hour"].tolist() == [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]


def test_build_prediction_curve_wraps_past_midnight():
    training = _make_training_frame()
    curve = mm.build_prediction_curve(
        model_pipeline=_StubPipeline(50.0),
        training=training,
        feature_columns=["hour"],
        model_name="Ridge",
        sample=training.iloc[0],
        hours=12,
        start_hour=22,  # wraps past midnight
    )
    assert curve["hour"].tolist() == [22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_build_prediction_curve_score_bounds_and_level_legal():
    training = _make_training_frame()
    curve = mm.build_prediction_curve(
        model_pipeline=_StubPipeline(85.0),
        training=training,
        feature_columns=["hour"],
        model_name="Ridge",
        sample=training.iloc[0],
    )
    assert (curve["predicted_score"] >= 0).all()
    assert (curve["predicted_score"] <= 100).all()
    assert set(curve["predicted_level"].unique()).issubset({"quiet", "moderate", "busy"})
    assert (curve["predicted_level"] == "busy").all()  # 85 → busy


def test_build_prediction_curve_clips_above_100():
    training = _make_training_frame()
    curve = mm.build_prediction_curve(
        model_pipeline=_StubPipeline(999.0),  # way above range
        training=training,
        feature_columns=["hour"],
        model_name="Ridge",
        sample=training.iloc[0],
    )
    assert (curve["predicted_score"] <= 100).all()

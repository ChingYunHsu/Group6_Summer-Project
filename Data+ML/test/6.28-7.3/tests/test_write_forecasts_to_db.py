"""Offline tests for write_forecasts_to_db (DB-3 forecast write contract).

No DB required — these cover the pure conversion/contract functions.
Run: python -m pytest Data+ML/test/6.28-7.3/tests/test_write_forecasts_to_db.py
"""

import csv
import os
import sys
from datetime import datetime

# Make the sibling src/ importable when run via plain pytest.
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import write_forecasts_to_db as w  # noqa: E402


def test_clamp_score_bounds_to_0_100():
    assert w.clamp_score(0) == 0
    assert w.clamp_score(100) == 100
    assert w.clamp_score(150) == 100  # DB CHECK would reject > 100
    assert w.clamp_score(-5) == 0
    assert w.clamp_score(48.41) == 48
    assert w.clamp_score(48.6) == 49


def test_next_occurrence_is_strictly_future():
    # A Saturday afternoon (2026-07-04 14:00). Next Monday 08:00 is 2026-07-06.
    now = datetime(2026, 7, 4, 14, 0)  # Saturday
    got = w.next_occurrence("monday", 8, now)
    assert got == datetime(2026, 7, 6, 8, 0)
    assert got > now


def test_next_occurrence_rolls_to_next_week_when_hour_passed():
    # Monday 10:00 asking for monday hour 8 → already passed → next week.
    now = datetime(2026, 7, 6, 10, 0)  # Monday
    got = w.next_occurrence("monday", 8, now)
    assert got == datetime(2026, 7, 13, 8, 0)
    assert got > now


def test_next_occurrence_same_day_future_hour():
    now = datetime(2026, 7, 6, 6, 0)  # Monday 06:00
    got = w.next_occurrence("monday", 8, now)
    assert got == datetime(2026, 7, 6, 8, 0)


def test_forecast_datetimes_sorted_and_one_per_hour():
    now = datetime(2026, 7, 4, 14, 0)  # Saturday
    dts = w.forecast_datetimes("monday", [10, 8, 9, 19], now)
    assert dts == sorted(dts)
    assert [d.hour for d in dts] == [8, 9, 10, 19]
    assert all(d > now for d in dts)


def test_upsert_sql_is_idempotent_on_duplicate_key():
    dt = datetime(2026, 7, 6, 8, 0)
    sql = w.upsert_sql("v_1001", dt, 48, "moderate", None, "ridge-v1")
    assert "INSERT INTO busyness_forecasts" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "v_1001" in sql
    assert "2026-07-06 08:00:00" in sql
    assert "ridge-v1" in sql
    assert "NULL" in sql  # estimated_wait_minutes omitted


def test_model_version_map_covers_csv_models():
    # prediction_curve_v1.csv uses these three model_name values.
    assert w.MODEL_VERSION_MAP["Ridge"] == "ridge-v1"
    assert w.MODEL_VERSION_MAP["RandomForestRegressor"] == "rf-v1"
    assert w.MODEL_VERSION_MAP["GradientBoostingRegressor"] == "gbm-v1"


def test_load_rows_filters_to_chosen_model(tmp_path):
    csv_path = tmp_path / "curve.csv"
    csv_path.write_text(
        "model_name,venue_id,prediction_group_id,day_of_week,hour,predicted_score,predicted_level\n"
        "Ridge,h1,ChIJx,monday,8,48.41,moderate\n"
        "Ridge,h1,ChIJx,monday,9,47.78,moderate\n"
        "RandomForestRegressor,h1,ChIJx,monday,8,50.0,busy\n"
    )
    ridge = w.load_rows(str(csv_path), "ridge-v1")
    assert len(ridge) == 2
    assert all(r["model_version"] == "ridge-v1" for r in ridge)
    assert all(r["place_id"] == "ChIJx" for r in ridge)

    rf = w.load_rows(str(csv_path), "rf-v1")
    assert len(rf) == 1
    assert rf[0]["model_version"] == "rf-v1"


def test_load_rows_clamps_score(tmp_path):
    csv_path = tmp_path / "curve.csv"
    csv_path.write_text(
        "model_name,venue_id,prediction_group_id,day_of_week,hour,predicted_score,predicted_level\n"
        "Ridge,h1,ChIJx,monday,8,150.0,busy\n"
    )
    rows = w.load_rows(str(csv_path), "ridge-v1")
    assert rows[0]["predicted_score"] == 100  # clamped to satisfy DB CHECK


def test_dry_run_emits_one_statement_per_row_and_writes_nothing(tmp_path, capsys, monkeypatch):
    csv_path = tmp_path / "curve.csv"
    csv_path.write_text(
        "model_name,venue_id,prediction_group_id,day_of_week,hour,predicted_score,predicted_level\n"
        "Ridge,h1,ChIJx,monday,8,48.41,moderate\n"
        "Ridge,h1,ChIJx,monday,9,47.78,moderate\n"
    )
    rc = w.main(["--dry-run", "--csv", str(csv_path), "--model-version", "ridge-v1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("INSERT INTO busyness_forecasts") == 2
    assert "0 written to DB" in out


def test_default_mode_is_dry_run_not_silent_write(tmp_path, capsys, monkeypatch):
    """No --dry-run and no --execute must default to dry-run (SOP 3 rollback control)."""
    csv_path = tmp_path / "curve.csv"
    csv_path.write_text(
        "model_name,venue_id,prediction_group_id,day_of_week,hour,predicted_score,predicted_level\n"
        "Ridge,h1,ChIJx,monday,8,48.41,moderate\n"
    )

    def _fail():
        raise AssertionError("_connect must not be called in dry-run mode")

    monkeypatch.setattr(w, "_connect", _fail)
    rc = w.main(["--csv", str(csv_path)])
    assert rc == 0
    assert "0 written to DB" in capsys.readouterr().out

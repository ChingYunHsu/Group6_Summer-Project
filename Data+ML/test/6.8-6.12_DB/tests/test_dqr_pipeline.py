import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


def _sample_data():
    venues = pd.DataFrame(
        {
            "venue_id": ["v1", "v2"],
            "venue_type": ["clinic", "pharmacy"],
            "name": ["Clinic", "Pharmacy"],
            "latitude": [40.75, 40.76],
            "longitude": [-73.99, -73.98],
            "district": ["midtown_east", "midtown_west"],
            "borough": ["Manhattan", "Manhattan"],
            "updated_at": ["2026-06-01", "2026-06-02"],
        }
    )
    return {
        "venues": venues,
        "restroom_profiles": pd.DataFrame(),
        "healthcare_profiles": pd.DataFrame(),
        "emergency_assets": pd.DataFrame(),
        "pedestrian_ramps": pd.DataFrame(),
        "venue_source_links": pd.DataFrame(),
        "busyness_scores": pd.DataFrame(),
        "external_context_cache": pd.DataFrame(),
        "user_reports": pd.DataFrame(),
    }


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_load_stage_closes_connection_and_summarizes(monkeypatch):
    from shared import dqr_pipeline

    conn = FakeConnection()
    data = _sample_data()
    monkeypatch.setattr(dqr_pipeline, "get_conn", lambda: conn)
    monkeypatch.setattr(
        dqr_pipeline, "query_table", lambda table, connection: data[table]
    )

    result = dqr_pipeline.load_stage()

    assert conn.closed is True
    assert result.venues_df.equals(data["venues"])
    assert result.tables_loaded == 1
    assert result.total_rows == 2
    assert result.load_errors == {}


def test_load_stage_rejects_missing_required_venues(monkeypatch):
    from shared import dqr_pipeline

    conn = FakeConnection()
    monkeypatch.setattr(dqr_pipeline, "get_conn", lambda: conn)
    monkeypatch.setattr(
        dqr_pipeline,
        "query_table",
        lambda table, connection: pd.DataFrame(),
    )

    with pytest.raises(RuntimeError, match="venues"):
        dqr_pipeline.load_stage()

    assert conn.closed is True


def test_load_stage_records_optional_table_errors(monkeypatch):
    from shared import dqr_pipeline

    conn = FakeConnection()
    venues = _sample_data()["venues"]
    monkeypatch.setattr(dqr_pipeline, "get_conn", lambda: conn)

    def fake_query(table, connection):
        if table == "venues":
            return venues
        if table == "user_reports":
            raise RuntimeError("table unavailable")
        return pd.DataFrame()

    monkeypatch.setattr(dqr_pipeline, "query_table", fake_query)

    result = dqr_pipeline.load_stage()

    assert result.load_errors == {"user_reports": "table unavailable"}
    assert result.data["user_reports"].empty


def test_stage_chain_returns_dataclasses_without_mutating_input(monkeypatch, tmp_path):
    from shared import dqr_pipeline

    data = _sample_data()
    original = data["venues"].copy(deep=True)

    analysis = dqr_pipeline.analysis_stage(data)
    assert analysis.event_types["actual"] == []
    assert analysis.event_types["missing"]
    quality = dqr_pipeline.quality_stage(data, data["venues"])
    anomaly = dqr_pipeline.anomaly_stage(data)
    scoring = dqr_pipeline.scoring_stage(
        data,
        data["venues"],
        anomaly,
        quality.coord_valid_mask,
    )
    cleaning = dqr_pipeline.cleaning_stage(
        data["venues"],
        quality.coord_valid_mask,
        analysis.record_analysis,
    )

    monkeypatch.setattr(
        dqr_pipeline, "fetch_traffic_hourly", lambda year=2025: pd.DataFrame()
    )
    monkeypatch.setattr(
        dqr_pipeline, "fetch_and_clean_weather", lambda **kwargs: pd.DataFrame()
    )
    external = dqr_pipeline.external_stage()
    final = dqr_pipeline.finalize_stage(
        data=data,
        venues_df=data["venues"],
        analysis=analysis,
        anomaly=anomaly,
        scoring=scoring,
        cleaning=cleaning,
        external=external,
        tables_loaded=1,
        total_rows=2,
        output_dir=tmp_path,
    )

    assert data["venues"].equals(original)
    assert scoring.total_score >= 0
    assert cleaning.venues_clean is not data["venues"]
    assert external.errors == {}
    assert not final.audit.empty
    assert "venues_count" in final.ml_usability


def test_external_stage_isolates_traffic_and_weather_failures(monkeypatch):
    from shared import dqr_pipeline

    monkeypatch.setattr(
        dqr_pipeline,
        "fetch_traffic_hourly",
        lambda year=2025: (_ for _ in ()).throw(RuntimeError("traffic offline")),
    )
    monkeypatch.setattr(
        dqr_pipeline,
        "fetch_and_clean_weather",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("weather offline")),
    )

    result = dqr_pipeline.external_stage()

    assert result.traffic_clean.empty
    assert result.weather_clean.empty
    assert result.errors == {
        "traffic": "traffic offline",
        "weather": "weather offline",
    }


def test_shared_package_imports_from_supported_working_directories(tmp_path):
    project_root = Path(__file__).resolve().parents[4]
    test_root = project_root / "Data+ML" / "test"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(test_root)
    code = "from shared.dqr_pipeline import load_stage; print(load_stage.__name__)"

    for cwd in (project_root, Path(__file__).resolve().parents[1], tmp_path):
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stdout.strip() == "load_stage"

"""
Tests for shared DQR modules — covers D2.7, GPS grid, export overwrite,
import independence, and clean_venues immutability.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ── D2.7: Database Integrity ──────────────────────────────────

class TestD27Integrity:
    """check_database_integrity must pass when all venues have districts."""

    def test_pass_all_districts_present(self):
        from dqr_checks import check_database_integrity
        df = pd.DataFrame({
            'venue_id': ['a', 'b', 'c'],
            'district': ['downtown', 'midtown_east', 'uptown'],
            'latitude': [40.71, 40.76, 40.82],
            'longitude': [-74.00, -73.97, -73.95],
        })
        result = check_database_integrity(df)
        assert result['passed'] is True
        assert result['score'] == 100.0
        assert result['metrics']['null_district'] == 0

    def test_fail_null_districts(self):
        from dqr_checks import check_database_integrity
        df = pd.DataFrame({
            'venue_id': ['a', 'b', 'c'],
            'district': ['downtown', None, 'uptown'],
            'latitude': [40.71, 40.76, 40.82],
            'longitude': [-74.00, -73.97, -73.95],
        })
        result = check_database_integrity(df)
        assert result['passed'] is False
        assert result['metrics']['null_district'] == 1

    def test_diagnoses_zero_gps_cause(self):
        from dqr_checks import check_database_integrity
        df = pd.DataFrame({
            'venue_id': ['a', 'b'],
            'district': [None, None],
            'latitude': [0, 40.76],
            'longitude': [0, -73.97],
        })
        result = check_database_integrity(df)
        assert result['passed'] is False
        assert any('GPS (0,0)' in i for i in result['issues'])

    def test_empty_df(self):
        from dqr_checks import check_database_integrity
        result = check_database_integrity(pd.DataFrame())
        assert result['passed'] is False

    def test_missing_district_column(self):
        from dqr_checks import check_database_integrity
        df = pd.DataFrame({'venue_id': ['a'], 'latitude': [40.7], 'longitude': [-74.0]})
        result = check_database_integrity(df)
        assert result['passed'] is False


# ── GPS Grid Latitude Scaling ─────────────────────────────────

class TestGPSGrid:
    """detect_gps_duplicates must catch points within threshold even at high lat."""

    def test_28m_apart_at_40_88(self):
        """28m apart in longitude at lat 40.88 (Manhattan north end)."""
        from dqr_analysis import detect_gps_duplicates
        from math import cos, radians

        lat = 40.88
        lng1 = -73.95
        lng2 = lng1 + 28 / (111320 * cos(radians(lat)))

        df_a = pd.DataFrame({'venue_id': ['v1'], 'name': ['A'], 'latitude': [lat], 'longitude': [lng1]})
        df_b = pd.DataFrame({'ramp_id': ['r1'], 'name': ['B'], 'latitude': [lat], 'longitude': [lng2]})

        result = detect_gps_duplicates({'venues': df_a, 'pedestrian_ramps': df_b}, threshold_m=30)
        assert len(result) >= 1, f'Expected ≥1 duplicate pair, got {len(result)}'

    def test_no_false_positive_at_100m(self):
        """100m apart should NOT be flagged."""
        from dqr_analysis import detect_gps_duplicates

        df_a = pd.DataFrame({'venue_id': ['v1'], 'name': ['A'], 'latitude': [40.75], 'longitude': [-73.98]})
        df_b = pd.DataFrame({'ramp_id': ['r1'], 'name': ['B'], 'latitude': [40.75], 'longitude': [-73.979]})

        result = detect_gps_duplicates({'venues': df_a, 'pedestrian_ramps': df_b}, threshold_m=30)
        assert len(result) == 0


# ── Export Overwrite ───────────────────────────────────────────

class TestExportOverwrite:
    """Empty DataFrames must delete stale CSVs, not leave them."""

    def test_empty_deletes_stale_file(self):
        from dqr_io import export_dqr_artifacts

        with tempfile.TemporaryDirectory() as tmpdir:
            stale = Path(tmpdir) / 'dqr_outliers.csv'
            stale.write_text('old,data\n1,2\n')
            assert stale.exists()

            export_dqr_artifacts(tmpdir, anomalies=pd.DataFrame())
            assert not stale.exists(), 'Stale dqr_outliers.csv was not deleted'

    def test_nonempty_writes_file(self):
        from dqr_io import export_dqr_artifacts

        with tempfile.TemporaryDirectory() as tmpdir:
            df = pd.DataFrame({'col': [1, 2, 3]})
            export_dqr_artifacts(tmpdir, anomalies=df)
            assert (Path(tmpdir) / 'dqr_outliers.csv').exists()


# ── Import Path Independence ──────────────────────────────────

class TestImportPath:
    """Modules must be importable regardless of cwd."""

    def test_import_from_any_cwd(self, tmp_path):
        import importlib
        import sys

        # Temporarily change cwd and verify import still works
        original = sys.path.copy()
        shared = str(Path(__file__).resolve().parents[2] / 'shared')
        if shared not in sys.path:
            sys.path.insert(0, shared)

        try:
            import dqr_checks
            import dqr_analysis
            import dqr_io
            import dqr_cleaning
            import external_ingestion
            assert hasattr(dqr_checks, 'check_database_integrity')
            assert hasattr(dqr_analysis, 'detect_gps_duplicates')
        finally:
            sys.path = original


# ── clean_venues Immutability ──────────────────────────────────

class TestCleanVenues:
    """clean_venues must not mutate the input DataFrame."""

    def test_input_not_mutated(self):
        from dqr_cleaning import clean_venues

        df = pd.DataFrame({
            'venue_id': ['a', 'b'],
            'venue_type': ['restroom', 'healthcare'],
            'name': ['X', 'Y'],
            'latitude': [40.71, 40.76],
            'longitude': [-74.00, -73.97],
            'district': ['downtown', 'midtown_east'],
        })
        original_cols = set(df.columns)
        original_len = len(df)

        clean_venues(df)

        assert set(df.columns) == original_cols, 'Input columns were modified'
        assert len(df) == original_len, 'Input row count was modified'

    def test_returns_new_dataframe(self):
        from dqr_cleaning import clean_venues

        df = pd.DataFrame({
            'venue_id': ['a'],
            'venue_type': ['restroom'],
            'name': ['X'],
            'latitude': [40.71],
            'longitude': [-74.00],
            'district': ['downtown'],
        })
        result = clean_venues(df)
        assert result is not df

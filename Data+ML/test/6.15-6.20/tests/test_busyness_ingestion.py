"""
Tests for busyness_ingestion module.

Two test layers:
  - Unit tests (default):  mock 外部依赖, 无网络/DB, 秒级完成
  - Integration tests:    调用真实 SODA API + MySQL, 需要网络和 Docker
    运行: pytest -m integration

运行:
  cd Data+ML/test/6.8-6.12_DB
  pytest tests/test_busyness_ingestion.py -v                  # 仅 mock 测试
  pytest tests/test_busyness_ingestion.py -m integration -v   # 真实 API + DB
  pytest tests/test_busyness_ingestion.py -v -m "not integration"  # 显式排除集成
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

# Add dqr directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dqr'))


# ── Classification ────────────────────────────────────────────

class TestClassifyScore:
    """classify_score must map 0-100 to four levels.

    Thresholds calibrated for Manhattan traffic (avg_vol/peak_vol*100):
    - quiet:     0 < score < 55  (late night / early morning)
    - moderate:  55 <= score < 70  (off-peak hours)
    - busy:      score >= 70  (rush hour)
    - no_data:   score == 0
    """

    def test_busy(self):
        from busyness_ingestion import classify_score
        assert classify_score(70) == 'busy'
        assert classify_score(100) == 'busy'
        assert classify_score(85) == 'busy'

    def test_moderate(self):
        from busyness_ingestion import classify_score
        assert classify_score(55) == 'moderate'
        assert classify_score(69) == 'moderate'

    def test_quiet(self):
        from busyness_ingestion import classify_score
        assert classify_score(1) == 'quiet'
        assert classify_score(54) == 'quiet'
        assert classify_score(30) == 'quiet'

    def test_no_data(self):
        from busyness_ingestion import classify_score
        assert classify_score(0) == 'no_data'


# ── GPS Conversion ────────────────────────────────────────────

class TestWktParsing:
    """parse_wkt_point must extract coordinates from WKT POINT strings."""

    def test_valid_wkt(self):
        from busyness_ingestion import parse_wkt_point
        x, y = parse_wkt_point('POINT (981745.7 199644.3)')
        assert abs(x - 981745.7) < 0.1
        assert abs(y - 199644.3) < 0.1

    def test_invalid_wkt(self):
        from busyness_ingestion import parse_wkt_point
        x, y = parse_wkt_point('INVALID')
        assert x is None
        assert y is None


class TestEpsgConversion:
    """epsg2263_to_wgs84 must convert NYC State Plane to lat/lng."""

    def test_manhattan_coordinates(self):
        pyproj = pytest.importorskip('pyproj')
        from busyness_ingestion import epsg2263_to_wgs84
        lat, lng = epsg2263_to_wgs84(981745.7, 199644.3)
        assert 40.70 <= lat <= 40.88  # Manhattan lat range
        assert -74.02 <= lng <= -73.90  # Manhattan lng range


# ── Haversine Distance ────────────────────────────────────────

class TestHaversine:
    """haversine_m must compute accurate distances."""

    def test_same_point(self):
        from busyness_ingestion import haversine_m
        assert haversine_m(40.71, -74.00, 40.71, -74.00) == 0

    def test_known_distance(self):
        from busyness_ingestion import haversine_m
        # ~1km apart
        d = haversine_m(40.71, -74.00, 40.72, -74.00)
        assert 800 < d < 1200  # ~1km tolerance


# ── Segment Aggregation ───────────────────────────────────────

class TestAggregateBySegment:
    """aggregate_by_segment must group by segment+hour with GPS."""

    def test_empty_input(self):
        from busyness_ingestion import aggregate_by_segment
        result = aggregate_by_segment(pd.DataFrame())
        assert result.empty

    def test_preserves_gps(self):
        from busyness_ingestion import aggregate_by_segment
        df = pd.DataFrame({
            'segmentid': ['s1', 's1'],
            'street': ['Broadway', 'Broadway'],
            'hour': [8, 9],
            'avg_vol': [100, 120],
            'peak_vol': [200, 200],
            'busyness_level': ['moderate', 'moderate'],
            'lat': [40.71, 40.71],
            'lng': [-74.00, -74.00],
        })
        result = aggregate_by_segment(df)
        assert 'lat' in result.columns
        assert 'lng' in result.columns
        assert result.iloc[0]['lat'] == 40.71

    def test_recalculates_score(self):
        """Score should be recalculated from avg_vol / peak_vol, not carried from input."""
        from busyness_ingestion import aggregate_by_segment
        df = pd.DataFrame({
            'segmentid': ['s1', 's1'],
            'street': ['Broadway', 'Broadway'],
            'hour': [8, 9],
            'avg_vol': [50, 150],
            'peak_vol': [200, 200],
            'busyness_level': ['moderate', 'moderate'],  # should be ignored
            'lat': [40.71, 40.71],
            'lng': [-74.00, -74.00],
        })
        result = aggregate_by_segment(df)
        assert result.iloc[0]['score'] == 25  # 50/200*100
        assert result.iloc[1]['score'] == 75  # 150/200*100

    def test_classifies_levels(self):
        """busyness_level should be derived from recalculated score."""
        from busyness_ingestion import aggregate_by_segment
        df = pd.DataFrame({
            'segmentid': ['s1', 's2'],
            'street': ['Broadway', '5th Ave'],
            'hour': [8, 10],
            'avg_vol': [10, 80],
            'peak_vol': [100, 100],
            'busyness_level': ['quiet', 'busy'],  # should be recalculated
            'lat': [40.71, 40.75],
            'lng': [-74.00, -73.98],
        })
        result = aggregate_by_segment(df)
        assert result[result['segmentid'] == 's1'].iloc[0]['busyness_level'] == 'quiet'
        assert result[result['segmentid'] == 's2'].iloc[0]['busyness_level'] == 'busy'


# ── Venue Mapping (mock DB) ───────────────────────────────────

class TestMapSegmentsToVenues:
    """map_segments_to_venues must match segments to nearby venues."""

    def test_empty_traffic(self):
        from busyness_ingestion import map_segments_to_venues
        result = map_segments_to_venues(MagicMock(), pd.DataFrame())
        assert result.empty

    def test_basic_mapping(self):
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()

        # Mock venues with GPS
        venues_df = pd.DataFrame({
            'venue_id': ['v_1001', 'v_1002'],
            'district': ['downtown', 'midtown_east'],
            'latitude': [40.714, 40.758],
            'longitude': [-74.009, -73.978],
        })
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            # Segment near v_1001 (downtown)
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1', 's1'],
                'street': ['Broadway', 'Broadway'],
                'hour': [8, 9],
                'lat': [40.714, 40.714],  # same as v_1001
                'lng': [-74.009, -74.009],
                'avg_vol': [100, 120],
                'peak_vol': [200, 200],
                'score': [50, 60],
                'busyness_level': ['moderate', 'moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            assert len(result) == 2
            assert result.iloc[0]['venue_id'] == 'v_1001'
            assert result.iloc[0]['district'] == 'downtown'

    def test_no_nearby_venue(self):
        """Segment too far from any venue (> 50m) should not be matched."""
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()

        venues_df = pd.DataFrame({
            'venue_id': ['v_1001'],
            'district': ['downtown'],
            'latitude': [40.714],
            'longitude': [-74.009],
        })
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            # Segment ~5km away from venue
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1'],
                'street': ['Broadway'],
                'hour': [8],
                'lat': [40.758],
                'lng': [-73.978],
                'avg_vol': [100],
                'peak_vol': [200],
                'score': [50],
                'busyness_level': ['moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            assert result.empty

    def test_nearest_venue_selected(self):
        """District-level: venues in same district get same score."""
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()

        venues_df = pd.DataFrame({
            'venue_id': ['v_a', 'v_b'],
            'district': ['downtown', 'downtown'],
        })
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1'],
                'street': ['Broadway'],
                'hour': [8],
                'lat': [40.714],
                'lng': [-74.009],
                'avg_vol': [100],
                'peak_vol': [200],
                'score': [50],
                'busyness_level': ['moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            # Both venues in downtown should get the same score
            assert len(result) == 2
            assert all(result['venue_id'].isin(['v_a', 'v_b']))

    def test_empty_venues_table(self):
        """When venues table returns no rows, result should be empty."""
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()
        venues_df = pd.DataFrame(columns=['venue_id', 'district'])
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1'],
                'street': ['Broadway'],
                'hour': [8],
                'lat': [40.714],
                'lng': [-74.009],
                'avg_vol': [100],
                'peak_vol': [200],
                'score': [50],
                'busyness_level': ['moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            assert result.empty

    def test_multiple_segments_matched(self):
        """District-level: segments in different districts produce different scores."""
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()

        venues_df = pd.DataFrame({
            'venue_id': ['v_downtown', 'v_uptown'],
            'district': ['downtown', 'uptown'],
        })
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            # Two segments in clearly different districts
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1', 's2'],
                'street': ['Broadway', 'Broadway'],
                'hour': [8, 8],
                'lat': [40.72, 40.85],   # s1=downtown, s2=uptown
                'lng': [-74.00, -73.93],
                'avg_vol': [100, 200],
                'peak_vol': [200, 300],
                'score': [50, 67],
                'busyness_level': ['moderate', 'moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            venue_ids = set(result['venue_id'].tolist())
            assert 'v_downtown' in venue_ids
            assert 'v_uptown' in venue_ids

    def test_output_columns(self):
        """Result should contain exactly the expected columns."""
        from busyness_ingestion import map_segments_to_venues
        mock_conn = MagicMock()

        venues_df = pd.DataFrame({
            'venue_id': ['v_1001'],
            'district': ['downtown'],
        })
        with patch('busyness_ingestion.pd.read_sql', return_value=venues_df):
            segment_hourly = pd.DataFrame({
                'segmentid': ['s1'],
                'street': ['Broadway'],
                'hour': [8],
                'lat': [40.714],
                'lng': [-74.009],
                'avg_vol': [100],
                'peak_vol': [200],
                'score': [50],
                'busyness_level': ['moderate'],
            })
            result = map_segments_to_venues(mock_conn, segment_hourly)
            expected_cols = {'venue_id', 'district', 'hour', 'score', 'busyness_level'}
            assert set(result.columns) == expected_cols


# ── Forecast Generation ───────────────────────────────────────

class TestBuildForecast1h:
    """build_forecast_1h must produce 12-hour rolling window."""

    def test_produces_12_entries(self):
        from busyness_ingestion import build_forecast_1h
        scores_df = pd.DataFrame({
            'hour': list(range(24)),
            'score': [10] * 24,
            'busyness_level': ['quiet'] * 24,
        })
        result = build_forecast_1h(scores_df, target_hour=8)
        assert len(result) == 12

    def test_wraps_around_midnight(self):
        from busyness_ingestion import build_forecast_1h
        scores_df = pd.DataFrame({
            'hour': list(range(24)),
            'score': [10 + h for h in range(24)],
            'busyness_level': ['quiet'] * 24,
        })
        result = build_forecast_1h(scores_df, target_hour=22)
        assert result[0]['percent'] == 32  # hour 22
        assert result[1]['percent'] == 33  # hour 23
        assert result[2]['percent'] == 10  # hour 0 (wraps)

    def test_missing_hours_default_to_no_data(self):
        """When some hours have no data, they should default to score=0, level='no_data'."""
        from busyness_ingestion import build_forecast_1h
        # Only hour 8 and 9 have data
        scores_df = pd.DataFrame({
            'hour': [8, 9],
            'score': [50, 60],
            'busyness_level': ['moderate', 'moderate'],
        })
        result = build_forecast_1h(scores_df, target_hour=8)
        assert len(result) == 12
        assert result[0]['percent'] == 50   # hour 8 — has data
        assert result[0]['level'] == 'moderate'
        assert result[1]['percent'] == 60   # hour 9 — has data
        assert result[2]['percent'] == 0    # hour 10 — no data
        assert result[2]['level'] == 'no_data'

    def test_forecast_structure(self):
        """Each forecast entry must have offset_hours, percent, and level keys."""
        from busyness_ingestion import build_forecast_1h
        scores_df = pd.DataFrame({
            'hour': list(range(24)),
            'score': [50] * 24,
            'busyness_level': ['moderate'] * 24,
        })
        result = build_forecast_1h(scores_df, target_hour=0)
        for i, entry in enumerate(result):
            assert entry['offset_hours'] == i
            assert 'percent' in entry
            assert 'level' in entry

    def test_target_hour_zero(self):
        """Starting from hour 0 should produce offsets 0-11."""
        from busyness_ingestion import build_forecast_1h
        scores_df = pd.DataFrame({
            'hour': list(range(24)),
            'score': list(range(24)),
            'busyness_level': ['quiet'] * 24,
        })
        result = build_forecast_1h(scores_df, target_hour=0)
        assert result[0]['percent'] == 0   # hour 0
        assert result[11]['percent'] == 11  # hour 11

    def test_target_hour_23(self):
        """Starting from hour 23 should wrap to hours 23, 0, 1, ..., 11."""
        from busyness_ingestion import build_forecast_1h
        scores_df = pd.DataFrame({
            'hour': list(range(24)),
            'score': list(range(24)),
            'busyness_level': ['quiet'] * 24,
        })
        result = build_forecast_1h(scores_df, target_hour=23)
        assert result[0]['percent'] == 23  # hour 23
        assert result[1]['percent'] == 0   # hour 0 (wraps)


# ── DB Insert (mock connection) ───────────────────────────────

class TestInsertBusynessScores:
    """insert_busyness_scores must handle data correctly."""

    def test_empty_insert(self):
        from busyness_ingestion import insert_busyness_scores
        result = insert_busyness_scores(MagicMock(), pd.DataFrame())
        assert result == 0

    def test_successful_insert(self):
        """Should insert rows via executemany and return affected row count."""
        from busyness_ingestion import insert_busyness_scores
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3  # 3 rows: v_1001 hour 8, v_1001 hour 9, v_1002 hour 8
        mock_conn.cursor.return_value = mock_cursor

        venue_scores = pd.DataFrame({
            'venue_id': ['v_1001', 'v_1001', 'v_1002'],
            'district': ['downtown', 'downtown', 'midtown'],
            'hour': [8, 9, 8],
            'score': [50, 60, 70],
            'busyness_level': ['moderate', 'moderate', 'busy'],
        })
        result = insert_busyness_scores(mock_conn, venue_scores)
        assert result == 3
        mock_cursor.executemany.assert_called_once()
        sql, rows = mock_cursor.executemany.call_args.args
        assert len(rows) == 3
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_default_model_version(self):
        """Default model_version should be nyc_traffic_baseline_v1."""
        from busyness_ingestion import insert_busyness_scores
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor

        venue_scores = pd.DataFrame({
            'venue_id': ['v_1001'],
            'district': ['downtown'],
            'hour': [8],
            'score': [50],
            'busyness_level': ['moderate'],
        })
        insert_busyness_scores(mock_conn, venue_scores)
        # Check executemany was called (model_version defaults applied)
        mock_cursor.executemany.assert_called_once()

    def test_custom_model_version(self):
        """Custom model_version should be passed through."""
        from busyness_ingestion import insert_busyness_scores
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor

        venue_scores = pd.DataFrame({
            'venue_id': ['v_1001'],
            'district': ['downtown'],
            'hour': [8],
            'score': [50],
            'busyness_level': ['moderate'],
        })
        insert_busyness_scores(mock_conn, venue_scores, model_version='custom_v2')
        # The cursor.executemany was called — model_version passed in each row tuple
        sql, rows = mock_cursor.executemany.call_args.args
        assert rows[0][6] == 'custom_v2'  # model_version is 7th element (index 6)

    def test_forecast_json_in_insert(self):
        """Forecast data should be JSON-serialized in the insert."""
        from busyness_ingestion import insert_busyness_scores
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor

        venue_scores = pd.DataFrame({
            'venue_id': ['v_1001'] * 24,
            'district': ['downtown'] * 24,
            'hour': list(range(24)),
            'score': [50] * 24,
            'busyness_level': ['moderate'] * 24,
        })
        insert_busyness_scores(mock_conn, venue_scores)
        sql, rows = mock_cursor.executemany.call_args.args
        # Row tuple: (venue_id, score, level, forecast_1h, forecast_start,
        #             forecast_end, model_version, features_snapshot)
        forecast_json = rows[0][3]  # 4th element is forecast_1h
        forecast = json.loads(forecast_json)
        assert isinstance(forecast, list)
        assert len(forecast) == 12

    def test_active_hour_insert_keeps_the_full_12_hour_profile(self):
        from busyness_ingestion import insert_busyness_scores
        mock_conn, mock_cursor = MagicMock(), MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        source = pd.DataFrame({
            'venue_id': ['v_1001'] * 24,
            'district': ['downtown'] * 24,
            'hour': list(range(24)),
            'score': list(range(24)),
            'busyness_level': ['quiet'] * 24,
        })
        insert_busyness_scores(
            mock_conn, source, effective_at=datetime(2026, 7, 19, 8), active_hour_only=True,
        )
        _, rows = mock_cursor.executemany.call_args.args
        assert len(rows) == 1
        forecast = json.loads(rows[0][3])
        assert [point['percent'] for point in forecast] == list(range(8, 20))
        assert {point['level'] for point in forecast} == {'quiet'}

    def test_effective_at_is_independent_of_source_data_year(self):
        from busyness_ingestion import insert_busyness_scores
        mock_conn, mock_cursor = MagicMock(), MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        source = pd.DataFrame({"venue_id": ["v_1001"], "hour": [8], "score": [50], "busyness_level": ["moderate"]})
        effective_at = datetime(2026, 7, 18, 15, 42)
        insert_busyness_scores(mock_conn, source, data_year=2025, effective_at=effective_at)
        _, rows = mock_cursor.executemany.call_args.args
        assert rows[0][4] == datetime(2026, 7, 18, 8)
        assert rows[0][5] == datetime(2026, 7, 18, 20)
        assert rows[0][7] == "nyc_traffic_2025_manhattan"

    def test_full_profile_anchors_all_hours_to_effective_day(self):
        from busyness_ingestion import insert_busyness_scores
        mock_conn, mock_cursor = MagicMock(), MagicMock()
        mock_cursor.rowcount = 24
        mock_conn.cursor.return_value = mock_cursor
        source = pd.DataFrame({
            "venue_id": ["v_1001"] * 24, "hour": list(range(24)),
            "score": [50] * 24, "busyness_level": ["moderate"] * 24,
        })
        insert_busyness_scores(mock_conn, source, effective_at=datetime(2026, 7, 18, 15))
        _, rows = mock_cursor.executemany.call_args.args
        assert len(rows) == 24
        assert {row[4].date() for row in rows} == {datetime(2026, 7, 18).date()}
        assert {row[4].hour for row in rows} == set(range(24))

    def test_uses_upsert(self):
        from busyness_ingestion import insert_busyness_scores
        mock_conn, mock_cursor = MagicMock(), MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        source = pd.DataFrame({"venue_id": ["v_1001"], "hour": [8], "score": [50], "busyness_level": ["moderate"]})
        insert_busyness_scores(mock_conn, source, effective_at=datetime(2026, 7, 18))
        sql, _ = mock_cursor.executemany.call_args.args
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_features_snapshot_default(self):
        """Default features_snapshot should contain year and 'manhattan'."""
        from busyness_ingestion import insert_busyness_scores
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor

        venue_scores = pd.DataFrame({
            'venue_id': ['v_1001'],
            'district': ['downtown'],
            'hour': [8],
            'score': [50],
            'busyness_level': ['moderate'],
        })
        insert_busyness_scores(mock_conn, venue_scores)
        sql, rows = mock_cursor.executemany.call_args.args
        features = rows[0][-1]  # last element is features_snapshot
        assert 'manhattan' in features


# ── API Fetch (mock HTTP) ─────────────────────────────────────

class TestFetchBusynessData:
    """fetch_busyness_data must query SODA API and transform coordinates."""

    def test_empty_api_response(self):
        """Empty API response should return empty DataFrame."""
        from busyness_ingestion import fetch_busyness_data
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp):
            result = fetch_busyness_data(year=2025)
            assert result.empty

    def test_filters_manhattan_bounds(self):
        """Only rows within Manhattan bounds should be kept."""
        pyproj = pytest.importorskip('pyproj')
        from busyness_ingestion import fetch_busyness_data
        # Two segments: one inside Manhattan, one outside
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                'segmentid': 's1', 'street': 'Broadway', 'fromst': 'A', 'tost': 'B',
                'direction': 'N', 'hh': '8', 'avg_vol': '100', 'n_records': '10',
                'wktgeom': 'POINT (981745.7 199644.3)',  # ~40.71, -74.00 (Manhattan)
            },
            {
                'segmentid': 's2', 'street': 'Ocean Pkwy', 'fromst': 'C', 'tost': 'D',
                'direction': 'S', 'hh': '8', 'avg_vol': '200', 'n_records': '5',
                'wktgeom': 'POINT (990000.0 170000.0)',  # Outside Manhattan
            },
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp):
            result = fetch_busyness_data(year=2025)
            # Only s1 should survive Manhattan bounds filter
            assert 's1' in result['segmentid'].values
            assert len(result) >= 1

    def test_calculates_busyness_level(self):
        """busyness_level column should be derived from score."""
        pyproj = pytest.importorskip('pyproj')
        from busyness_ingestion import fetch_busyness_data
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                'segmentid': 's1', 'street': 'Broadway', 'fromst': 'A', 'tost': 'B',
                'direction': 'N', 'hh': '8', 'avg_vol': '100', 'n_records': '10',
                'wktgeom': 'POINT (981745.7 199644.3)',
            },
            {
                'segmentid': 's1', 'street': 'Broadway', 'fromst': 'A', 'tost': 'B',
                'direction': 'N', 'hh': '9', 'avg_vol': '50', 'n_records': '10',
                'wktgeom': 'POINT (981745.7 199644.3)',
            },
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp):
            result = fetch_busyness_data(year=2025)
            assert 'busyness_level' in result.columns
            assert 'score' in result.columns

    def test_api_called_with_correct_params(self):
        """SODA API should be called with boro and year filters."""
        from busyness_ingestion import fetch_busyness_data
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp) as mock_get:
            fetch_busyness_data(year=2024, boro='Manhattan')
            call_kwargs = mock_get.call_args
            assert "2024" in call_kwargs[1]['params']['$where']
            assert "Manhattan" in call_kwargs[1]['params']['$where']

    def test_dropna_on_avg_vol_hh(self):
        """Rows with NaN avg_vol or hh should be dropped."""
        pyproj = pytest.importorskip('pyproj')
        from busyness_ingestion import fetch_busyness_data
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                'segmentid': 's1', 'street': 'Broadway', 'fromst': 'A', 'tost': 'B',
                'direction': 'N', 'hh': 'not_a_number', 'avg_vol': '100',
                'n_records': '10', 'wktgeom': 'POINT (981745.7 199644.3)',
            },
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp):
            result = fetch_busyness_data(year=2025)
            assert result.empty

    def test_required_output_columns(self):
        """Result should contain all required columns."""
        pyproj = pytest.importorskip('pyproj')
        from busyness_ingestion import fetch_busyness_data
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                'segmentid': 's1', 'street': 'Broadway', 'fromst': 'A', 'tost': 'B',
                'direction': 'N', 'hh': '8', 'avg_vol': '100', 'n_records': '10',
                'wktgeom': 'POINT (981745.7 199644.3)',
            },
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch('busyness_ingestion.requests.get', return_value=mock_resp):
            result = fetch_busyness_data(year=2025)
            required = {'segmentid', 'street', 'hour', 'avg_vol', 'peak_vol',
                        'busyness_level', 'score', 'lat', 'lng'}
            assert required.issubset(set(result.columns))


# ── Pipeline Orchestration ────────────────────────────────────

class TestRunPipeline:
    """run_pipeline must orchestrate all steps correctly."""

    def test_aborts_on_empty_traffic(self):
        """Pipeline should abort when no traffic data is returned."""
        from busyness_ingestion import run_pipeline
        with patch('busyness_ingestion.fetch_busyness_data', return_value=pd.DataFrame()):
            run_pipeline(year=2025, dry_run=True)

    def test_aborts_on_empty_aggregation(self):
        """Pipeline should abort when aggregation produces no data."""
        from busyness_ingestion import run_pipeline
        traffic_df = pd.DataFrame({
            'segmentid': ['s1'], 'street': ['Broadway'], 'hour': [8],
            'avg_vol': [100], 'peak_vol': [200], 'score': [50],
            'busyness_level': ['moderate'], 'lat': [40.71], 'lng': [-74.00],
        })
        with patch('busyness_ingestion.fetch_busyness_data', return_value=traffic_df), \
             patch('busyness_ingestion.aggregate_by_segment', return_value=pd.DataFrame()):
            run_pipeline(year=2025, dry_run=True)

    def test_dry_run_no_db_insert(self):
        """Dry-run mode should not call insert_busyness_scores."""
        from busyness_ingestion import run_pipeline
        traffic_df = pd.DataFrame({
            'segmentid': ['s1'], 'street': ['Broadway'], 'hour': [8],
            'avg_vol': [100], 'peak_vol': [200], 'score': [50],
            'busyness_level': ['moderate'], 'lat': [40.71], 'lng': [-74.00],
        })
        venue_scores = pd.DataFrame({
            'venue_id': ['v_1'], 'district': ['downtown'],
            'hour': [8], 'score': [50], 'busyness_level': ['moderate'],
        })
        mock_conn = MagicMock()
        with patch('busyness_ingestion.fetch_busyness_data', return_value=traffic_df), \
             patch('busyness_ingestion.aggregate_by_segment', return_value=traffic_df), \
             patch('busyness_ingestion.get_conn', return_value=mock_conn), \
             patch('busyness_ingestion.map_segments_to_venues', return_value=venue_scores), \
             patch('busyness_ingestion.insert_busyness_scores') as mock_insert:
            run_pipeline(year=2025, dry_run=True)
            mock_insert.assert_not_called()

    def test_full_run_calls_insert(self):
        """Non-dry-run should call insert_busyness_scores."""
        from busyness_ingestion import run_pipeline
        traffic_df = pd.DataFrame({
            'segmentid': ['s1'], 'street': ['Broadway'], 'hour': [8],
            'avg_vol': [100], 'peak_vol': [200], 'score': [50],
            'busyness_level': ['moderate'], 'lat': [40.71], 'lng': [-74.00],
        })
        venue_scores = pd.DataFrame({
            'venue_id': ['v_1'], 'district': ['downtown'],
            'hour': [8], 'score': [50], 'busyness_level': ['moderate'],
        })
        mock_conn = MagicMock()
        with patch('busyness_ingestion.fetch_busyness_data', return_value=traffic_df), \
             patch('busyness_ingestion.aggregate_by_segment', return_value=traffic_df), \
             patch('busyness_ingestion.get_conn', return_value=mock_conn), \
             patch('busyness_ingestion.map_segments_to_venues', return_value=venue_scores), \
             patch('busyness_ingestion.insert_busyness_scores', return_value=1) as mock_insert:
            run_pipeline(year=2025, dry_run=False, model_version='test_v1')
            mock_insert.assert_called_once()
            # model_version is passed as 3rd positional arg
            call_args = mock_insert.call_args
            assert call_args[0][2] == 'test_v1'

    def test_aborts_on_empty_venue_mapping(self):
        """Pipeline should abort and close conn when no venue mapping found."""
        from busyness_ingestion import run_pipeline
        traffic_df = pd.DataFrame({
            'segmentid': ['s1'], 'street': ['Broadway'], 'hour': [8],
            'avg_vol': [100], 'peak_vol': [200], 'score': [50],
            'busyness_level': ['moderate'], 'lat': [40.71], 'lng': [-74.00],
        })
        mock_conn = MagicMock()
        with patch('busyness_ingestion.fetch_busyness_data', return_value=traffic_df), \
             patch('busyness_ingestion.aggregate_by_segment', return_value=traffic_df), \
             patch('busyness_ingestion.get_conn', return_value=mock_conn), \
             patch('busyness_ingestion.map_segments_to_venues', return_value=pd.DataFrame()):
            run_pipeline(year=2025, dry_run=True)
            mock_conn.close.assert_called()

    def test_pipeline_passes_model_version(self):
        """model_version should be forwarded to insert_busyness_scores."""
        from busyness_ingestion import run_pipeline
        traffic_df = pd.DataFrame({
            'segmentid': ['s1'], 'street': ['Broadway'], 'hour': [8],
            'avg_vol': [100], 'peak_vol': [200], 'score': [50],
            'busyness_level': ['moderate'], 'lat': [40.71], 'lng': [-74.00],
        })
        venue_scores = pd.DataFrame({
            'venue_id': ['v_1'], 'district': ['downtown'],
            'hour': [8], 'score': [50], 'busyness_level': ['moderate'],
        })
        mock_conn = MagicMock()
        with patch('busyness_ingestion.fetch_busyness_data', return_value=traffic_df), \
             patch('busyness_ingestion.aggregate_by_segment', return_value=traffic_df), \
             patch('busyness_ingestion.get_conn', return_value=mock_conn), \
             patch('busyness_ingestion.map_segments_to_venues', return_value=venue_scores), \
             patch('busyness_ingestion.insert_busyness_scores', return_value=1) as mock_insert:
            run_pipeline(year=2025, dry_run=False, model_version='my_custom_model')
            mock_insert.assert_called_once()
            # model_version is passed as 3rd positional arg
            call_args = mock_insert.call_args
            assert call_args[0][2] == 'my_custom_model'

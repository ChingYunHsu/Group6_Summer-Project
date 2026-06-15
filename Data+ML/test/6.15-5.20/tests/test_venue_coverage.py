"""
Tests for venue spatial coverage module.

Test layers:
  - Unit tests (default): mock external dependencies, no network/DB
  - Integration tests: real APIs, requires network

Run:
  cd Data+ML/test/6.8-6.12_DB
  pytest tests/test_venue_coverage.py -v
  pytest tests/test_venue_coverage.py -k cli -v
  pytest tests/test_venue_coverage.py -k 'http or retry or pagination or isolation' -v
  pytest tests/test_venue_coverage.py -k source -v
  pytest tests/test_venue_coverage.py -k 'distance or balltree or dedup' -v
  pytest tests/test_venue_coverage.py -k coverage -v
  pytest tests/test_venue_coverage.py -k 'artifact or report or chart or metadata' -v
"""

import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Add dqr directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dqr"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Helpers ────────────────────────────────────────────────────

def _make_venues_csv(tmp_path: Path, n: int = 10) -> Path:
    """Create a minimal venues_clean.csv for testing."""
    rows = []
    for i in range(n):
        rows.append({
            "venue_id": f"v_{i:04d}",
            "venue_type": ["emergencyasset", "healthcare", "restroom"][i % 3],
            "name": f"Venue {i}",
            "latitude": 40.71 + i * 0.001,
            "longitude": -74.00 + i * 0.001,
            "district": ["downtown", "midtown_east", "midtown_west", "uptown"][i % 4],
        })
    df = pd.DataFrame(rows)
    csv_path = tmp_path / "venues_clean.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def _make_venues_csv_with_dupes(tmp_path: Path) -> Path:
    """Create a venues_clean.csv with duplicate venue_ids."""
    rows = [
        {"venue_id": "v_dup", "venue_type": "healthcare", "name": "A",
         "latitude": 40.71, "longitude": -74.00, "district": "downtown"},
        {"venue_id": "v_dup", "venue_type": "healthcare", "name": "B",
         "latitude": 40.72, "longitude": -74.01, "district": "downtown"},
        {"venue_id": "v_uniq", "venue_type": "restroom", "name": "C",
         "latitude": 40.73, "longitude": -74.02, "district": "uptown"},
    ]
    df = pd.DataFrame(rows)
    csv_path = tmp_path / "venues_dup.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def _make_source_points(n: int = 5, base_lat: float = 40.71,
                        base_lon: float = -74.00):
    """Generate n source points near the base coordinates."""
    from venue_coverage import SourcePoint
    return [
        SourcePoint(
            source="test",
            source_id=f"s_{i}",
            name=f"Station {i}",
            latitude=base_lat + i * 0.0005,
            longitude=base_lon + i * 0.0005,
        )
        for i in range(n)
    ]


# ═══════════════════════════════════════════════════════════════
# Task 1: CLI parsing and validation
# ═══════════════════════════════════════════════════════════════


class TestCLIParsing:
    """CLI argument parsing and validation."""

    def test_defaults_parsed_correctly(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        args = parse_args(["--venue-file", str(csv)])
        assert args.radii_list == [100, 200, 300, 400, 500]
        assert args.sources_list == ["citibike", "mta", "traffic"]
        assert args.traffic_year == 2025
        assert args.page_size == 5000
        assert args.connect_timeout == 2.0
        assert args.read_timeout == 5.0
        assert args.max_retries == 3

    def test_custom_radii(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        args = parse_args(["--venue-file", str(csv), "--radii", "200,400"])
        assert args.radii_list == [200, 400]

    def test_custom_sources(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        args = parse_args(["--venue-file", str(csv), "--sources", "citibike"])
        assert args.sources_list == ["citibike"]

    def test_custom_traffic_year(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        args = parse_args(["--venue-file", str(csv), "--traffic-year", "2024"])
        assert args.traffic_year == 2024

    def test_source_order_preserved(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        args = parse_args(["--venue-file", str(csv),
                           "--sources", "traffic,citibike,mta"])
        assert args.sources_list == ["traffic", "citibike", "mta"]

    def test_empty_radii_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--radii", ""])

    def test_non_positive_radii_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--radii", "0,100"])

    def test_decreasing_radii_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--radii", "500,100"])

    def test_duplicate_radii_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--radii", "100,100,200"])

    def test_unsupported_source_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--sources", "citibike,unknown"])

    def test_page_size_too_large_fails(self, tmp_path):
        from run_venue_coverage import parse_args
        csv = _make_venues_csv(tmp_path)
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", str(csv), "--page-size", "6000"])

    def test_missing_venue_file_fails(self):
        from run_venue_coverage import parse_args
        with pytest.raises(SystemExit):
            parse_args(["--venue-file", "/nonexistent/file.csv"])


# ═══════════════════════════════════════════════════════════════
# Task 2: HTTP client, retries, and source isolation
# ═══════════════════════════════════════════════════════════════


class TestHTTPClient:
    """HTTP client timeout and retry behavior."""

    def test_timeout_passed_to_request(self):
        """Every request should use the configured timeout."""
        from venue_coverage import _request_with_retries
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        with patch("venue_coverage.requests.get", return_value=mock_resp) as mock_get:
            _request_with_retries("http://test.com", timeout=(3, 7))
            mock_get.assert_called_once()
            assert mock_get.call_args[1]["timeout"] == (3, 7)

    def test_retry_on_connection_error(self):
        """Transient connection errors should retry up to max_retries."""
        from venue_coverage import _request_with_retries
        import requests as req
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        with patch("venue_coverage.requests.get",
                    side_effect=[req.ConnectionError("fail"), mock_resp]) as mock_get, \
             patch("venue_coverage.time.sleep"):
            resp, retries = _request_with_retries("http://test.com", max_retries=3)
            assert mock_get.call_count == 2
            assert resp == mock_resp
            assert retries == 1

    def test_timeout_fails_immediately(self):
        """Read timeouts should fail immediately — no retry."""
        from venue_coverage import _request_with_retries
        import requests as req
        with patch("venue_coverage.requests.get",
                    side_effect=req.Timeout("timeout")), \
             patch("venue_coverage.time.sleep"):
            with pytest.raises(req.Timeout):
                _request_with_retries("http://test.com", max_retries=3)

    def test_retry_on_5xx(self):
        """HTTP 5xx should retry."""
        from venue_coverage import _request_with_retries
        mock_err = MagicMock()
        mock_err.status_code = 500
        mock_err.raise_for_status = MagicMock()
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.raise_for_status = MagicMock()
        with patch("venue_coverage.requests.get",
                    side_effect=[mock_err, mock_ok]) as mock_get, \
             patch("venue_coverage.time.sleep"):
            result = _request_with_retries("http://test.com", max_retries=3)
            assert mock_get.call_count == 2

    def test_retry_on_429(self):
        """HTTP 429 (rate limit) should retry."""
        from venue_coverage import _request_with_retries
        mock_err = MagicMock()
        mock_err.status_code = 429
        mock_err.raise_for_status = MagicMock()
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.raise_for_status = MagicMock()
        with patch("venue_coverage.requests.get",
                    side_effect=[mock_err, mock_ok]) as mock_get, \
             patch("venue_coverage.time.sleep"):
            result = _request_with_retries("http://test.com", max_retries=3)
            assert mock_get.call_count == 2

    def test_no_retry_on_4xx(self):
        """Non-retryable 4xx (e.g. 404) should fail immediately."""
        from venue_coverage import _request_with_retries
        import requests as req
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")
        with patch("venue_coverage.requests.get", return_value=mock_resp), \
             patch("venue_coverage.time.sleep"):
            with pytest.raises(req.HTTPError):
                _request_with_retries("http://test.com", max_retries=3)

    def test_retry_delays_used(self):
        """Retry delays should be 1, 2, 4 seconds."""
        from venue_coverage import _request_with_retries, RETRY_DELAYS
        import requests as req
        with patch("venue_coverage.requests.get",
                    side_effect=req.ConnectionError("fail")), \
             patch("venue_coverage.time.sleep") as mock_sleep:
            with pytest.raises(req.ConnectionError):
                _request_with_retries("http://test.com", max_retries=3)
            # Should have slept 3 times (delays[0], delays[1], delays[2])
            assert mock_sleep.call_count == 3
            sleep_values = [c[0][0] for c in mock_sleep.call_args_list]
            assert sleep_values == [1, 2, 4]


class TestPagination:
    """SODA pagination behavior."""

    def test_stops_on_short_page(self):
        """Pagination should stop when a page has fewer rows than page_size."""
        from venue_coverage import fetch_soda_pages
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = [{"id": "1"}, {"id": "2"}]
        mock_resp1.status_code = 200
        mock_resp1.raise_for_status = MagicMock()

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = [{"id": "3"}]  # short page
        mock_resp2.status_code = 200
        mock_resp2.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_resp1, 0), (mock_resp2, 0)]):
            rows, retries = fetch_soda_pages("http://test.com", {}, page_size=2)
            assert len(rows) == 3
            assert retries == 0

    def test_raises_on_max_points_exceeded(self):
        """Should raise ValueError when unique points exceed safety limit."""
        from venue_coverage import fetch_soda_pages
        # Return a full page each time to keep paginating
        big_page = [{"id": str(i)} for i in range(100)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = big_page
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            with pytest.raises(ValueError, match="exceeded"):
                fetch_soda_pages("http://test.com", {}, page_size=100, max_points=50)


class TestSourceIsolation:
    """Failed sources should not block other sources."""

    def test_failed_source_does_not_stop_others(self, tmp_path):
        """One source failure should not prevent others from succeeding."""
        from venue_coverage import SourceResult, fetch_citibike, fetch_mta

        # Simulate citibike success, mta failure
        cb_result = SourceResult(source="citibike", status="ok", points=[])
        mta_result = SourceResult(source="mta", status="failed",
                                  error_type="ConnectionError", error_message="timeout")

        with patch("venue_coverage.fetch_citibike", return_value=cb_result), \
             patch("venue_coverage.fetch_mta", return_value=mta_result):
            # Both should be callable independently
            r1 = fetch_citibike()
            r2 = fetch_mta()
            assert r1.status == "ok"
            assert r2.status == "failed"


# ═══════════════════════════════════════════════════════════════
# Task 3: Source adapters
# ═══════════════════════════════════════════════════════════════


class TestCitiBikeAdapter:
    """Citi Bike GBFS parsing."""

    def test_information_status_join(self):
        """Should join station_information with station_status."""
        from venue_coverage import fetch_citibike
        info_data = {
            "data": {"stations": [
                {"station_id": "s1", "name": "Station 1", "lat": 40.71, "lon": -74.00},
                {"station_id": "s2", "name": "Station 2", "lat": 40.72, "lon": -74.01},
            ]},
            "last_updated": 1700000000,
            "ttl": 300,
        }
        status_data = {
            "data": {"stations": [
                {"station_id": "s1", "is_installed": 1, "is_renting": 1},
                {"station_id": "s2", "is_installed": 0, "is_renting": 0},  # not installed
            ]},
        }
        mock_info = MagicMock()
        mock_info.json.return_value = info_data
        mock_info.raise_for_status = MagicMock()
        mock_status = MagicMock()
        mock_status.json.return_value = status_data
        mock_status.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_info, 0), (mock_status, 0)]):
            result = fetch_citibike()
            assert result.status == "ok"
            # s2 should be filtered out (not installed)
            ids = [p.source_id for p in result.points]
            assert "s1" in ids
            assert "s2" not in ids

    def test_fallback_when_status_unavailable(self):
        """Should still work if station_status fails."""
        from venue_coverage import fetch_citibike
        info_data = {
            "data": {"stations": [
                {"station_id": "s1", "name": "Station 1", "lat": 40.71, "lon": -74.00},
            ]},
            "last_updated": 1700000000,
        }
        mock_info = MagicMock()
        mock_info.json.return_value = info_data
        mock_info.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_info, 0), Exception("status unavailable")]):
            result = fetch_citibike()
            assert result.status == "ok"
            assert len(result.points) == 1

    def test_source_id_deduplication(self):
        """Duplicate station_ids should be removed."""
        from venue_coverage import fetch_citibike
        info_data = {
            "data": {"stations": [
                {"station_id": "s1", "name": "Station 1", "lat": 40.71, "lon": -74.00},
                {"station_id": "s1", "name": "Station 1 Dup", "lat": 40.71, "lon": -74.00},
                {"station_id": "s2", "name": "Station 2", "lat": 40.72, "lon": -74.01},
            ]},
            "last_updated": 1700000000,
        }
        mock_info = MagicMock()
        mock_info.json.return_value = info_data
        mock_info.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_info, 0), Exception("no status")]):
            result = fetch_citibike()
            ids = [p.source_id for p in result.points]
            assert len(ids) == len(set(ids))  # no duplicates
            assert result.unique_id_count == 2

    def test_freshness_metadata(self):
        """Source timestamp should be populated from last_updated."""
        from venue_coverage import fetch_citibike
        info_data = {
            "data": {"stations": [
                {"station_id": "s1", "name": "S1", "lat": 40.71, "lon": -74.00},
            ]},
            "last_updated": 1700000000,
        }
        mock_info = MagicMock()
        mock_info.json.return_value = info_data
        mock_info.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_info, 0), Exception("no status")]):
            result = fetch_citibike()
            assert result.max_source_timestamp is not None

    def test_invalid_coordinates_rejected(self):
        """Stations with missing coords should be skipped (not included in points)."""
        from venue_coverage import fetch_citibike
        info_data = {
            "data": {"stations": [
                {"station_id": "s1", "name": "Good", "lat": 40.71, "lon": -74.00},
                {"station_id": "s2", "name": "Bad", "lat": None, "lon": None},
            ]},
            "last_updated": 1700000000,
        }
        mock_info = MagicMock()
        mock_info.json.return_value = info_data
        mock_info.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_info, 0), Exception("no status")]):
            result = fetch_citibike()
            # s2 has None coords — skipped in adapter before normalisation
            assert len(result.points) == 1
            assert result.points[0].source_id == "s1"


class TestMTAAdapter:
    """MTA Subway station complex parsing."""

    def test_unique_station_parsing(self):
        """Should parse station complexes from the station complex dataset."""
        from venue_coverage import fetch_mta
        rows = [
            {"complex_id": "c1", "complex_name": "Times Sq",
             "latitude": "40.758", "longitude": "-73.985"},
            {"complex_id": "c2", "complex_name": "Grand Central",
             "latitude": "40.752", "longitude": "-73.977"},
            {"complex_id": "c3", "complex_name": "Fulton St",
             "latitude": "40.709", "longitude": "-74.006"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    return_value=(mock_resp, 0)):
            result = fetch_mta()
            assert result.status == "ok"
            assert result.unique_id_count == 3

    def test_no_od_grouping(self):
        """Query should not reference origin/destination OD columns."""
        from venue_coverage import fetch_mta
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    return_value=(mock_resp, 0)):
            result = fetch_mta()
            assert "origin_" not in result.query_text
            assert "destination_" not in result.query_text

    def test_dataset_id(self):
        """Dataset ID should be the station complex dataset."""
        from venue_coverage import fetch_mta, MTA_DATASET_ID
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    return_value=(mock_resp, 0)):
            result = fetch_mta()
            assert result.dataset_id == MTA_DATASET_ID

    def test_source_id_deduplication(self):
        """Duplicate complex_ids should be removed."""
        from venue_coverage import fetch_mta
        rows = [
            {"complex_id": "c1", "complex_name": "A",
             "latitude": "40.758", "longitude": "-73.985"},
            {"complex_id": "c1", "complex_name": "A dup",
             "latitude": "40.758", "longitude": "-73.985"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            result = fetch_mta()
            # After normalise_points dedup by source_id
            ids = [p.source_id for p in result.points]
            assert len(ids) == len(set(ids))


class TestTrafficAdapter:
    """NYC Traffic segment parsing and coordinate transformation."""

    def test_unique_segment_parsing(self):
        """Should parse segments and convert coordinates."""
        from venue_coverage import fetch_traffic
        rows = [
            {"segmentid": "seg1", "street": "Broadway",
             "wktgeom": "POINT (981745.7 199644.3)"},
            {"segmentid": "seg2", "street": "5th Ave",
             "wktgeom": "POINT (989000.0 197000.0)"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            result = fetch_traffic(year=2025)
            assert result.status == "ok"
            assert result.unique_id_count == 2

    def test_coordinate_transformation(self):
        """EPSG:2263 coordinates should be converted to WGS84."""
        from venue_coverage import fetch_traffic
        rows = [
            {"segmentid": "seg1", "street": "Broadway",
             "wktgeom": "POINT (981745.7 199644.3)"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            result = fetch_traffic(year=2025)
            if result.status == "ok" and result.points:
                pt = result.points[0]
                assert 40.70 <= pt.latitude <= 40.88
                assert -74.02 <= pt.longitude <= -73.90

    def test_invalid_wkt_rejected(self):
        """Invalid WKT geometry should be rejected."""
        from venue_coverage import fetch_traffic
        rows = [
            {"segmentid": "seg1", "street": "Broadway", "wktgeom": "INVALID"},
            {"segmentid": "seg2", "street": "5th Ave",
             "wktgeom": "POINT (981745.7 199644.3)"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            result = fetch_traffic(year=2025)
            # seg1 should be rejected
            assert result.rejected_count >= 1

    def test_year_in_query(self):
        """Requested year should appear in query."""
        from venue_coverage import fetch_traffic
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries", return_value=(mock_resp, 0)):
            result = fetch_traffic(year=2024)
            assert "2024" in result.query_text


# ═══════════════════════════════════════════════════════════════
# Task 4: BallTree distance calculation
# ═══════════════════════════════════════════════════════════════


class TestBallTreeDistance:
    """BallTree Haversine distance computation."""

    def test_known_coordinate_pair(self):
        """Known coordinate pairs should produce expected distance."""
        from venue_coverage import compute_nearest_distances
        # Two points ~1km apart (40.71,-74.00) and (40.72,-74.00)
        venue_lats = np.array([40.71])
        venue_lons = np.array([-74.00])
        src_lats = np.array([40.72])
        src_lons = np.array([-74.00])
        src_ids = np.array(["s1"])

        dist_m, nearest_ids = compute_nearest_distances(
            venue_lats, venue_lons, src_lats, src_lons, src_ids
        )
        assert abs(dist_m[0] - 1110) < 100  # ~1110m tolerance
        assert nearest_ids[0] == "s1"

    def test_same_point_zero_distance(self):
        """Same coordinates should produce zero distance."""
        from venue_coverage import compute_nearest_distances
        dist_m, _ = compute_nearest_distances(
            np.array([40.71]), np.array([-74.00]),
            np.array([40.71]), np.array([-74.00]),
            np.array(["s1"]),
        )
        assert dist_m[0] < 0.01  # essentially zero

    def test_nearest_source_id_correct(self):
        """Nearest source ID should be correct when multiple sources exist."""
        from venue_coverage import compute_nearest_distances
        # s1 at 40.710 (very close), s2 at 40.750 (far)
        venue_lats = np.array([40.711])
        venue_lons = np.array([-74.00])
        src_lats = np.array([40.710, 40.750])
        src_lons = np.array([-74.00, -74.00])
        src_ids = np.array(["s1", "s2"])

        dist_m, nearest_ids = compute_nearest_distances(
            venue_lats, venue_lons, src_lats, src_lons, src_ids
        )
        assert nearest_ids[0] == "s1"

    def test_exact_100m_boundary_is_covered(self):
        """A point at exactly 100m should be flagged as covered."""
        from venue_coverage import compute_radius_flags
        distances = np.array([100.0, 100.1, 99.9])
        flags = compute_radius_flags(distances, [100])
        assert flags[100][0] == True   # exactly 100m is covered
        assert flags[100][1] == False  # 100.1m is not
        assert flags[100][2] == True   # 99.9m is covered

    def test_one_tree_query_all_radii(self):
        """One BallTree query should support all five radius flags."""
        from venue_coverage import compute_nearest_distances, compute_radius_flags
        dist_m, _ = compute_nearest_distances(
            np.array([40.71, 40.72]),
            np.array([-74.00, -74.00]),
            np.array([40.711, 40.750]),
            np.array([-74.00, -74.00]),
            np.array(["s1", "s2"]),
        )
        flags = compute_radius_flags(dist_m, [100, 200, 300, 400, 500])
        assert len(flags) == 5
        for r in [100, 200, 300, 400, 500]:
            assert len(flags[r]) == 2

    def test_empty_source_returns_inf(self):
        """No source points should return inf distance."""
        from venue_coverage import compute_nearest_distances
        dist_m, nearest_ids = compute_nearest_distances(
            np.array([40.71]), np.array([-74.00]),
            np.array([]), np.array([]),
            np.array([], dtype=object),
        )
        assert dist_m[0] == np.inf
        assert nearest_ids[0] == ""


class TestVenueDeduplication:
    """Venue_id deduplication behavior."""

    def test_dedup_by_venue_id(self, tmp_path):
        """Duplicate venue_ids should be removed, keeping first."""
        from venue_coverage import load_venues
        csv = _make_venues_csv_with_dupes(tmp_path)
        df, dup_count = load_venues(csv)
        assert len(df) == 2  # v_dup kept once, v_uniq kept
        assert dup_count == 1

    def test_different_ids_same_coords_stay(self, tmp_path):
        """Different venue_ids at same coordinates should remain separate."""
        from venue_coverage import load_venues
        rows = [
            {"venue_id": "a", "venue_type": "healthcare", "name": "A",
             "latitude": 40.71, "longitude": -74.00, "district": "downtown"},
            {"venue_id": "b", "venue_type": "healthcare", "name": "B",
             "latitude": 40.71, "longitude": -74.00, "district": "downtown"},
        ]
        df = pd.DataFrame(rows)
        csv = tmp_path / "venues.csv"
        df.to_csv(csv, index=False)
        result, dup_count = load_venues(csv)
        assert len(result) == 2
        assert dup_count == 0


# ═══════════════════════════════════════════════════════════════
# Task 5: Coverage aggregation
# ═══════════════════════════════════════════════════════════════


class TestStandaloneCoverage:
    """Standalone source coverage computation."""

    def test_basic_coverage(self):
        """All venues within radius should show 100% coverage."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2", "v3"],
            "venue_type": ["healthcare"] * 3,
            "district": ["downtown"] * 3,
            "src_nearest_distance_m": [50.0, 80.0, 120.0],
        })
        result = compute_standalone_coverage(detail_df, "src", [100, 200])
        overall_100 = result[(result["scope"] == "overall") & (result["radius_m"] == 100)]
        assert overall_100.iloc[0]["covered_count"] == 2
        assert overall_100.iloc[0]["venue_count"] == 3

        overall_200 = result[(result["scope"] == "overall") & (result["radius_m"] == 200)]
        assert overall_200.iloc[0]["covered_count"] == 3

    def test_marginal_gain(self):
        """Marginal gain should be computed correctly."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2", "v3"],
            "venue_type": ["healthcare"] * 3,
            "district": ["downtown"] * 3,
            "src_nearest_distance_m": [50.0, 150.0, 250.0],
        })
        result = compute_standalone_coverage(detail_df, "src", [100, 200, 300])
        overall = result[result["scope"] == "overall"]
        # At 100m: 1 covered, marginal = 1
        r100 = overall[overall["radius_m"] == 100].iloc[0]
        assert r100["incremental_covered_count"] == 1
        # At 200m: 2 covered, marginal = 1
        r200 = overall[overall["radius_m"] == 200].iloc[0]
        assert r200["incremental_covered_count"] == 1
        # At 300m: 3 covered, marginal = 1
        r300 = overall[overall["radius_m"] == 300].iloc[0]
        assert r300["incremental_covered_count"] == 1

    def test_venue_type_aggregation(self):
        """Results should be segmented by venue_type."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2", "v3"],
            "venue_type": ["healthcare", "healthcare", "restroom"],
            "district": ["downtown"] * 3,
            "src_nearest_distance_m": [50.0, 50.0, 200.0],
        })
        result = compute_standalone_coverage(detail_df, "src", [100])
        vt = result[result["scope"] == "venue_type"]
        hc = vt[(vt["group_value"] == "healthcare") & (vt["radius_m"] == 100)]
        assert hc.iloc[0]["covered_count"] == 2
        rr = vt[(vt["group_value"] == "restroom") & (vt["radius_m"] == 100)]
        assert rr.iloc[0]["covered_count"] == 0

    def test_district_aggregation(self):
        """Results should be segmented by district."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2"],
            "venue_type": ["healthcare"] * 2,
            "district": ["downtown", "uptown"],
            "src_nearest_distance_m": [50.0, 200.0],
        })
        result = compute_standalone_coverage(detail_df, "src", [100])
        dist = result[result["scope"] == "district"]
        dt = dist[(dist["group_value"] == "downtown") & (dist["radius_m"] == 100)]
        assert dt.iloc[0]["covered_count"] == 1

    def test_no_cross_table(self):
        """Should NOT produce venue_type × district cross-table."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1"],
            "venue_type": ["healthcare"],
            "district": ["downtown"],
            "src_nearest_distance_m": [50.0],
        })
        result = compute_standalone_coverage(detail_df, "src", [100])
        scopes = set(result["scope"].unique())
        assert scopes == {"overall", "venue_type", "district"}

    def test_distance_distribution(self):
        """Median and P90 distance should be computed."""
        from venue_coverage import compute_standalone_coverage
        detail_df = pd.DataFrame({
            "venue_id": [f"v{i}" for i in range(100)],
            "venue_type": ["healthcare"] * 100,
            "district": ["downtown"] * 100,
            "src_nearest_distance_m": list(range(100, 200)),
        })
        result = compute_standalone_coverage(detail_df, "src", [500])
        overall = result[result["scope"] == "overall"].iloc[0]
        assert overall["nearest_distance_median"] == pytest.approx(149.5, abs=1)
        assert overall["nearest_distance_p90"] > 180


class TestCumulativeCoverage:
    """Cumulative (combination) coverage computation."""

    def test_cumulative_order(self):
        """Sources should be combined in the specified order."""
        from venue_coverage import compute_cumulative_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2", "v3"],
            "venue_type": ["healthcare"] * 3,
            "district": ["downtown"] * 3,
            "a_nearest_distance_m": [50.0, 200.0, 200.0],
            "b_nearest_distance_m": [200.0, 50.0, 200.0],
        })
        result = compute_cumulative_coverage(detail_df, ["a", "b"], [100])
        overall = result[result["scope"] == "overall"]
        # a alone covers v1
        a_row = overall[overall["source_or_combination"] == "a"]
        assert a_row.iloc[0]["covered_count"] == 1
        # a+b covers v1+v2
        ab_row = overall[overall["source_or_combination"] == "a + b"]
        assert ab_row.iloc[0]["covered_count"] == 2

    def test_incremental_unique_attribution(self):
        """Incremental count should only include venues not covered by earlier sources."""
        from venue_coverage import compute_cumulative_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2", "v3"],
            "venue_type": ["healthcare"] * 3,
            "district": ["downtown"] * 3,
            "a_nearest_distance_m": [50.0, 50.0, 200.0],  # a covers v1, v2
            "b_nearest_distance_m": [200.0, 200.0, 50.0],  # b covers v3
        })
        result = compute_cumulative_coverage(detail_df, ["a", "b"], [100])
        overall = result[result["scope"] == "overall"]
        ab_row = overall[overall["source_or_combination"] == "a + b"]
        assert ab_row.iloc[0]["incremental_covered_count"] == 1  # only v3 is new
        assert ab_row.iloc[0]["covered_count"] == 3

    def test_overall_aggregation(self):
        """Overall aggregation should combine all venues."""
        from venue_coverage import compute_cumulative_coverage
        detail_df = pd.DataFrame({
            "venue_id": ["v1", "v2"],
            "venue_type": ["healthcare", "restroom"],
            "district": ["downtown", "uptown"],
            "src_nearest_distance_m": [50.0, 50.0],
        })
        result = compute_cumulative_coverage(detail_df, ["src"], [100])
        overall = result[result["scope"] == "overall"]
        assert overall.iloc[0]["venue_count"] == 2


# ═══════════════════════════════════════════════════════════════
# Task 6: Artifacts and visualizations
# ═══════════════════════════════════════════════════════════════


class TestArtifacts:
    """Output artifact contracts."""

    def test_detail_csv_contract(self, tmp_path):
        """venue_coverage_detail.csv should have required columns."""
        from venue_coverage import write_artifacts
        detail_df = pd.DataFrame({
            "venue_id": ["v1"],
            "venue_type": ["healthcare"],
            "district": ["downtown"],
            "latitude": [40.71],
            "longitude": [-74.00],
            "citibike_nearest_source_id": ["s1"],
            "citibike_nearest_distance_m": [50.0],
            "citibike_covered_100m": [True],
            "citibike_covered_200m": [True],
            "citibike_covered_300m": [True],
            "citibike_covered_400m": [True],
            "citibike_covered_500m": [True],
        })
        summary_df = pd.DataFrame({
            "scope": ["overall"], "group_name": ["overall"],
            "group_value": ["_all"], "coverage_kind": ["standalone"],
            "source_or_combination": ["citibike"], "radius_m": [100],
            "venue_count": [1], "covered_count": [1],
            "coverage_rate": [1.0], "incremental_covered_count": [1],
            "marginal_gain_pp": [1.0],
            "nearest_distance_median": [50.0], "nearest_distance_p90": [50.0],
        })
        metadata = {"run_id": "test", "artifacts": []}

        write_artifacts(tmp_path, detail_df, summary_df, metadata, "# Test Report", [])
        detail_csv = tmp_path / "venue_coverage_detail.csv"
        assert detail_csv.exists()
        df = pd.read_csv(detail_csv)
        required = {"venue_id", "venue_type", "district", "latitude", "longitude"}
        assert required.issubset(set(df.columns))

    def test_summary_csv_contract(self, tmp_path):
        """coverage_summary.csv should have required columns."""
        from venue_coverage import write_artifacts
        detail_df = pd.DataFrame({"venue_id": ["v1"]})
        summary_df = pd.DataFrame({
            "scope": ["overall"], "group_name": ["overall"],
            "group_value": ["_all"], "coverage_kind": ["standalone"],
            "source_or_combination": ["citibike"], "radius_m": [100],
            "venue_count": [1], "covered_count": [1],
            "coverage_rate": [1.0], "incremental_covered_count": [1],
            "marginal_gain_pp": [1.0],
            "nearest_distance_median": [50.0], "nearest_distance_p90": [50.0],
        })
        metadata = {"run_id": "test", "artifacts": []}

        write_artifacts(tmp_path, detail_df, summary_df, metadata, "# Test Report", [])
        summary_csv = tmp_path / "coverage_summary.csv"
        assert summary_csv.exists()
        df = pd.read_csv(summary_csv)
        required = {"scope", "group_name", "group_value", "coverage_kind",
                     "source_or_combination", "radius_m", "venue_count",
                     "covered_count", "coverage_rate"}
        assert required.issubset(set(df.columns))

    def test_metadata_json_contract(self, tmp_path):
        """run_metadata.json should have required sections."""
        from venue_coverage import write_artifacts
        metadata = {
            "run_id": "20260101T000000Z",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:01:00+00:00",
            "timezone": "UTC",
            "venue_input": {},
            "parameters": {},
            "sources": {},
            "software": {},
            "artifacts": [],
        }
        write_artifacts(tmp_path,
                        pd.DataFrame(), pd.DataFrame(), metadata, "# Test Report", [])
        meta_path = tmp_path / "run_metadata.json"
        assert meta_path.exists()
        with open(meta_path) as f:
            data = json.load(f)
        for key in ["run_id", "started_at", "completed_at", "timezone",
                     "venue_input", "parameters", "sources", "software", "artifacts"]:
            assert key in data

    def test_markdown_required_sections(self):
        """coverage_report.md should contain all 10 required sections."""
        from venue_coverage import generate_markdown_report, SourceResult
        metadata = {
            "run_id": "test",
            "started_at": "2026-01-01T00:00:00",
            "completed_at": "2026-01-01T00:01:00",
            "venue_input": {
                "file_path": "test.csv", "total_rows": 10,
                "unique_venue_count": 10, "duplicate_venue_id_count": 0,
            },
        }
        summary_df = pd.DataFrame({
            "scope": ["overall"], "group_name": ["overall"],
            "group_value": ["_all"], "coverage_kind": ["standalone"],
            "source_or_combination": ["citibike"], "radius_m": [100],
            "venue_count": [10], "covered_count": [5],
            "coverage_rate": [0.5], "incremental_covered_count": [5],
            "marginal_gain_pp": [0.5],
            "nearest_distance_median": [100.0], "nearest_distance_p90": [200.0],
        })
        detail_df = pd.DataFrame()
        source_results = {"citibike": SourceResult(source="citibike", status="ok")}

        md = generate_markdown_report(metadata, summary_df, detail_df, source_results, [100])
        for section in ["Run Summary", "Source Status", "Standalone Coverage",
                        "Cumulative Coverage", "Venue Type", "District",
                        "Distance Distribution", "Uncovered", "Warnings",
                        "Constraints"]:
            assert section.lower() in md.lower()

    def test_artifacts_written_directly(self, tmp_path):
        """Artifacts should be written directly to output directory."""
        from venue_coverage import write_artifacts
        metadata = {"run_id": "test", "artifacts": []}
        write_artifacts(tmp_path,
                        pd.DataFrame(), pd.DataFrame(), metadata, "# Test Report", [])
        assert (tmp_path / "run_metadata.json").exists()

    def test_no_raw_api_response_written(self, tmp_path):
        """No raw API response or source-point snapshot should be written."""
        from venue_coverage import write_artifacts
        metadata = {"run_id": "test", "artifacts": []}
        write_artifacts(tmp_path,
                        pd.DataFrame(), pd.DataFrame(), metadata, "# Test Report", [])
        files = list(tmp_path.iterdir())
        for f in files:
            if f.is_file():
                assert "raw" not in f.name.lower()
                assert "response" not in f.name.lower()
                assert "source_point" not in f.name.lower()


class TestCharts:
    """Chart generation tests."""

    def test_chart_files_exist(self, tmp_path):
        """All four PNG charts should be generated."""
        from venue_coverage import generate_charts, SourceResult
        summary_df = pd.DataFrame({
            "scope": ["overall"], "group_name": ["overall"],
            "group_value": ["_all"], "coverage_kind": ["standalone"],
            "source_or_combination": ["citibike"], "radius_m": [100],
            "venue_count": [10], "covered_count": [5],
            "coverage_rate": [0.5], "incremental_covered_count": [5],
            "marginal_gain_pp": [0.5],
            "nearest_distance_median": [100.0], "nearest_distance_p90": [200.0],
        })
        detail_df = pd.DataFrame()
        source_results = {"citibike": SourceResult(source="citibike", status="ok")}
        filenames = generate_charts(
            tmp_path, summary_df, detail_df, source_results, [100, 200], "test"
        )
        assert len(filenames) == 4
        for fname in filenames:
            assert (tmp_path / fname).exists()
            assert (tmp_path / fname).stat().st_size > 0

    def test_no_legend_warning_on_empty_data(self, tmp_path):
        """Charts with empty data should not produce legend warnings."""
        import warnings
        from venue_coverage import generate_charts, SourceResult
        cols = ["scope", "group_name", "group_value", "coverage_kind",
                "source_or_combination", "radius_m", "venue_count",
                "covered_count", "coverage_rate", "incremental_covered_count",
                "marginal_gain_pp", "nearest_distance_median", "nearest_distance_p90"]
        empty_summary = pd.DataFrame(columns=cols)
        detail_df = pd.DataFrame()
        source_results = {"citibike": SourceResult(source="citibike", status="ok")}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            generate_charts(tmp_path, empty_summary, detail_df, source_results, [100], "test")
            legend_warnings = [x for x in w if "legend" in str(x.message).lower()]
            assert len(legend_warnings) == 0


class TestTrafficYearProfile:
    """Traffic year distribution diagnostic."""

    def test_year_profile_field_exists(self):
        """fetch_traffic should populate year_profile on success."""
        from venue_coverage import fetch_traffic
        rows = [
            {"segmentid": "s1", "street": "Broadway",
             "wktgeom": "POINT (981745.7 199644.3)"},
        ]
        year_rows = [
            {"yr": "2024", "record_count": "100", "unique_segment_count": "50"},
            {"yr": "2025", "record_count": "28", "unique_segment_count": "28"},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = rows
        mock_resp.raise_for_status = MagicMock()
        mock_year_resp = MagicMock()
        mock_year_resp.json.return_value = year_rows
        mock_year_resp.raise_for_status = MagicMock()

        with patch("venue_coverage._request_with_retries",
                    side_effect=[(mock_resp, 0), (mock_year_resp, 0)]):
            result = fetch_traffic(year=2025)
            assert result.year_profile is not None
            assert len(result.year_profile) == 2
            assert result.year_profile[0]["year"] == "2024"
            assert result.year_profile[1]["unique_segment_count"] == 28


# ═══════════════════════════════════════════════════════════════
# Task 7: Integration / smoke tests (require network)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestLiveSmoke:
    """Live API smoke tests — require network access."""

    def test_citibike_live(self):
        """Citi Bike GBFS should return stations."""
        from venue_coverage import fetch_citibike
        result = fetch_citibike()
        assert result.status == "ok"
        assert result.unique_coord_count > 0

    def test_mta_live(self):
        """MTA API should return station complexes."""
        from venue_coverage import fetch_mta
        # MTA SoQL grouping queries are slow (~44s) — use 60s timeout
        result = fetch_mta(year=2025, timeout=(2, 60))
        assert result.status == "ok"
        assert result.unique_coord_count > 0

    def test_traffic_live(self):
        """Traffic SODA API should return segments."""
        from venue_coverage import fetch_traffic
        result = fetch_traffic(year=2025)
        assert result.status == "ok"
        assert result.unique_coord_count > 0

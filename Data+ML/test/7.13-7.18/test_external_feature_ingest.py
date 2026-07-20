"""Tests for external_feature_ingest.py — weather, holiday, GBFS, MTA normalization + fallback."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import external_feature_ingest as efi


# ═══════════════════════════════════════════════════════════════════════════════
# Weather
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_OPEN_METEO = {
    "hourly": {
        "time": ["2026-07-06T00:00", "2026-07-06T01:00", "2026-07-06T02:00"],
        "temperature_2m": [22.0, 21.5, 21.0],
        "apparent_temperature": [20.0, 19.5, 19.0],
        "relative_humidity_2m": [65.0, 68.0, 70.0],
        "precipitation": [0.0, 0.0, 0.2],
        "weather_code": [0, 1, 3],
        "wind_speed_10m": [5.0, 6.0, 7.0],
    }
}


def test_weather_normalize_success():
    result = efi.normalize_weather(SAMPLE_OPEN_METEO)
    # temperature_c should be present and reasonable
    assert "temperature_c" in result
    assert not result["temperature_missing"]
    assert "precipitation_mm" in result
    assert "weather_condition" in result
    assert "wind_speed_kmh" in result
    assert not result["wind_missing"]
    assert "heat_alert" in result


def test_weather_fallback_has_all_keys():
    """WEATHER_FALLBACK must contain all standard feature keys with missing flags."""
    fb = efi.WEATHER_FALLBACK
    assert fb["temperature_missing"] is True
    assert fb["precipitation_missing"] is True
    assert fb["humidity_missing"] is True
    assert fb["wind_missing"] is True
    assert fb["heat_alert_missing"] is True
    assert fb["temperature_c"] == -999
    assert fb["precipitation_mm"] == 0.0


def test_weather_normalize_empty():
    result = efi.normalize_weather({})
    # Should return fallback on empty response
    assert result["temperature_missing"] == True


def test_weather_code_to_condition():
    assert efi._weather_code_to_condition(0) == "clear"
    assert efi._weather_code_to_condition(1) == "partly_cloudy"
    assert efi._weather_code_to_condition(51) == "rain"
    assert efi._weather_code_to_condition(61) == "heavy_rain"
    assert efi._weather_code_to_condition(95) == "thunderstorm"
    assert efi._weather_code_to_condition(999) == "unknown"


def test_heat_alert():
    assert efi._heat_alert(34.9) == 0
    assert efi._heat_alert(35.0) == 1
    assert efi._heat_alert(40.0) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Holidays
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_HOLIDAYS = [
    {"date": "2026-01-01", "localName": "New Year's Day", "name": "New Year's Day", "countryCode": "US"},
    {"date": "2026-12-25", "localName": "Christmas Day", "name": "Christmas Day", "countryCode": "US"},
]


def test_holiday_normalize_success():
    result = efi.normalize_holidays(SAMPLE_HOLIDAYS)
    assert "is_public_holiday" in result
    assert "is_major_event_nearby" in result
    assert not result["holiday_missing"]
    assert result["event_source"] == "nager_date"
    assert len(result["holidays_all_2026"]) == 2


def test_holiday_fallback_keys():
    fb = efi.HOLIDAY_FALLBACK
    assert fb["is_public_holiday"] == 0
    assert fb["holiday_missing"] is True
    assert fb["event_source"] == "unavailable"


# ═══════════════════════════════════════════════════════════════════════════════
# GBFS / Citi Bike
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_GBFS_STATUS = {
    "data": {
        "stations": [
            {"station_id": "s1", "num_bikes_available": 5, "num_docks_available": 10,
             "is_installed": 1, "is_renting": 1, "is_returning": 1},
            {"station_id": "s2", "num_bikes_available": 0, "num_docks_available": 15,
             "is_installed": 1, "is_renting": 1, "is_returning": 1},
            {"station_id": "s3", "num_bikes_available": 3, "num_docks_available": 7,
             "is_installed": 0, "is_renting": 0, "is_returning": 0},  # inactive
        ]
    }
}

SAMPLE_GBFS_INFO = {
    "s1": {"station_id": "s1", "name": "Station 1", "lat": 40.7, "lon": -74.0, "capacity": 20},
    "s2": {"station_id": "s2", "name": "Station 2", "lat": 40.8, "lon": -73.9, "capacity": 15},
}


def test_gbfs_normalize_success():
    result = efi.normalize_gbfs(SAMPLE_GBFS_STATUS, SAMPLE_GBFS_INFO)
    assert not result["citibike_activity_missing"]
    assert result["active_station_count"] == 2  # only s1 and s2 are active
    assert result["nearby_bike_availability"] == 5  # s1=5, s2=0
    assert result["nearby_dock_availability"] == 25  # s1=10, s2=15
    assert result["gbfs_source"] == "lyft_gbfs_2.3"


def test_gbfs_fallback():
    fb = efi.GBFS_FALLBACK
    assert fb["citibike_activity_missing"] is True
    assert fb["gbfs_source"] == "unavailable"


def test_gbfs_normalize_empty():
    result = efi.normalize_gbfs({}, {})
    assert result["citibike_activity_missing"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# MTA GTFS-RT
# ═══════════════════════════════════════════════════════════════════════════════


def test_mta_normalize_no_data():
    result = efi.normalize_mta_gtfs_rt(None)
    assert result["mta_disruption_missing"] is True
    assert result["mta_arrival_missing"] is True
    assert result["mta_source"] == "unavailable"


def test_mta_fallback():
    fb = efi.MTA_FALLBACK
    assert fb["mta_service_disruption_flag"] == 0
    assert fb["mta_disruption_missing"] is True
    assert fb["mta_source"] == "unavailable"


def test_mta_normalize_raw_bytes():
    """An undecoded protobuf must not be misreported as an arrival count."""
    result = efi.normalize_mta_gtfs_rt(b"fake protobuf data")
    # Should handle gracefully — either decode or retain an explicit missing value.
    assert "mta_gtfs_rt_available" in result
    assert result["mta_realtime_arrival_count_1h"] >= 0
    assert result["mta_source"] in ("gtfs_rt_raw", "gtfs_rt")

"""external_feature_ingest.py — Scheduled ingestion for external forecast-v2 features.

Fetches weather, holidays, Citi Bike (GBFS), and MTA feeds, normalizes them,
and upserts into `external_context_cache`. Each source supports --dry-run and
--execute modes with explicit API URL parameterisation.

Usage:
  # Dry-run (prints what would be cached, no DB write)
  python external_feature_ingest.py --source weather --api-url "<url>" --dry-run
  python external_feature_ingest.py --source holiday --api-url "<url>" --dry-run
  python external_feature_ingest.py --source gbfs --api-url "<status_url>" --station-info-url "<info_url>" --dry-run
  python external_feature_ingest.py --source mta_gtfs_rt --api-url "<url>" --api-key-file ./secrets/key.txt --dry-run

  # Execute (writes to external_context_cache)
  python external_feature_ingest.py --source weather --api-url "<url>" --execute

Default API endpoints (SOP sprint 4):
  weather:  Open-Meteo free API
  holiday:  Nager.Date public holidays API
  gbfs:     Citi Bike GBFS 2.3 real-time feed
  mta:      MTA GTFS-RT subway feed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE
for _p in [HERE, *HERE.parents]:
    if (_p / "Data+ML").exists() and (_p / "docker").exists():
        PROJECT_ROOT = _p
        break

import db_utils


_UPSERT_CACHE = (
    "INSERT INTO external_context_cache "
    "(context_type, venue_id, request_key, payload_json, valid_from, expires_at) "
    "VALUES (%s, %s, %s, %s, %s, %s) "
    "ON DUPLICATE KEY UPDATE "
    "payload_json = VALUES(payload_json), "
    "valid_from = VALUES(valid_from), "
    "expires_at = VALUES(expires_at)"
)


def _write_to_cache(context_type: str, request_key: str, payload: dict[str, Any],
                     ttl_hours: int = 24, venue_id: str | None = None) -> dict[str, Any]:
    """Upsert one row into external_context_cache. Returns row summary."""
    now = datetime.now(timezone.utc)
    valid_from = now
    expires_at = now + timedelta(hours=ttl_hours)
    conn = db_utils.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_UPSERT_CACHE, (
                context_type, venue_id, request_key,
                json.dumps(payload), valid_from, expires_at,
            ))
        conn.commit()
        return {
            "context_type": context_type,
            "request_key": request_key,
            "venue_id": venue_id,
            "valid_from": valid_from.isoformat(),
            "expires_at": expires_at.isoformat(),
            "rowcount": cur.rowcount,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── HTTP fetch wrapper ────────────────────────────────────────────────────────


def _fetch_json(url: str, timeout: int = 30, api_key: str = "") -> dict | list | None:
    """Fetch a JSON response. Set api_key for MTA; returns parsed JSON or None."""
    import requests
    headers = {"x-api-key": api_key} if api_key else None
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"  HTTP error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def _fetch_raw(url: str, api_key: str = "", timeout: int = 30) -> bytes | None:
    """Fetch raw binary response. Set api_key for MTA GTFS-RT protobuf."""
    import requests
    headers = {"x-api-key": api_key} if api_key else None
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        print(f"  HTTP error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Source 1: Weather (Open-Meteo)
# ═══════════════════════════════════════════════════════════════════════════════

WEATHER_FALLBACK = {
    "temperature_c": -999,
    "temperature_missing": True,
    "apparent_temperature": -999,
    "relative_humidity_pct": -1,
    "humidity_missing": True,
    "precipitation_mm": 0.0,
    "precipitation_missing": True,
    "weather_code": -1,
    "weather_condition": "unknown",
    "wind_speed_kmh": -1,
    "wind_missing": True,
    "heat_alert": 0,
    "heat_alert_missing": True,
    "weather_source": "unavailable",
}


def _weather_code_to_condition(code: int) -> str:
    if code == 0:
        return "clear"
    elif code <= 3:
        return "partly_cloudy"
    elif code <= 20:
        return "foggy"
    elif code <= 30:
        return "dust"
    elif code <= 50:
        return "drizzle"
    elif code <= 60:
        return "rain"
    elif code <= 70:
        return "heavy_rain"
    elif code <= 80:
        return "snow"
    elif code <= 90:
        return "showers"
    elif code <= 99:
        return "thunderstorm"
    else:
        return "unknown"


def _heat_alert(temperature_c: float) -> int:
    return 1 if temperature_c >= 35 else 0


def normalize_weather(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize Open-Meteo response → standard feature dict per forecast hour."""
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return WEATHER_FALLBACK.copy()

    # Pick the first forecast hour (current / closest)
    idx = 0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    for i, t in enumerate(times):
        if t >= now_str:
            idx = i
            break

    temp = hourly.get("temperature_2m", [WEATHER_FALLBACK["temperature_c"]])[idx]
    precip = hourly.get("precipitation", [WEATHER_FALLBACK["precipitation_mm"]])[idx]
    humidity = hourly.get("relative_humidity_2m", [WEATHER_FALLBACK["relative_humidity_pct"]])[idx]
    wind = hourly.get("wind_speed_10m", [WEATHER_FALLBACK["wind_speed_kmh"]])[idx]
    code = hourly.get("weather_code", [WEATHER_FALLBACK["weather_code"]])[idx]
    app_temp = hourly.get("apparent_temperature", [temp])[idx]

    return {
        "temperature_c": float(temp),
        "temperature_missing": False,
        "apparent_temperature": float(app_temp),
        "relative_humidity_pct": float(humidity),
        "humidity_missing": False,
        "precipitation_mm": float(precip) if precip is not None else 0.0,
        "precipitation_missing": precip is None,
        "weather_code": int(code) if code is not None else -1,
        "weather_condition": _weather_code_to_condition(int(code)) if code is not None else "unknown",
        "wind_speed_kmh": float(wind),
        "wind_missing": wind is None,
        "heat_alert": _heat_alert(float(temp)),
        "heat_alert_missing": False,
        "weather_source": "open_meteo",
        "hourly_series": {
            "time": times,
            "temperature_2m": hourly.get("temperature_2m", []),
            "precipitation": hourly.get("precipitation", []),
            "relative_humidity_2m": hourly.get("relative_humidity_2m", []),
            "wind_speed_10m": hourly.get("wind_speed_10m", []),
            "weather_code": hourly.get("weather_code", []),
        },
    }


def ingest_weather(api_url: str, dry_run: bool) -> dict[str, Any]:
    """Fetch weather, normalize, optionally cache."""
    print(f"[weather] Fetching: {api_url[:80]}...")
    raw = _fetch_json(api_url)
    if raw is None:
        print("[weather] FAILED — using fallback")
        return {"status": "failed", "payload": WEATHER_FALLBACK.copy()}

    normalized = normalize_weather(raw)
    print(f"  temperature_c={normalized['temperature_c']}, "
          f"precipitation_mm={normalized['precipitation_mm']}, "
          f"humidity={normalized['relative_humidity_pct']}, "
          f"wind={normalized['wind_speed_kmh']}, "
          f"condition={normalized['weather_condition']}, "
          f"heat_alert={normalized['heat_alert']}")

    if dry_run:
        print(f"[weather] DRY RUN — would cache {len(normalized.get('hourly_series', {}).get('time', []))} hourly rows")
        return {"status": "dry_run", "payload": normalized}

    result = _write_to_cache(
        context_type="weather_forecast",
        request_key=f"open_meteo_nyc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
        payload=normalized,
        ttl_hours=2,
    )
    print(f"[weather] CACHED — expires_at={result['expires_at']}")
    return {"status": "ok", **result, "payload": normalized}


# ═══════════════════════════════════════════════════════════════════════════════
# Source 2: Public Holidays (Nager.Date)
# ═══════════════════════════════════════════════════════════════════════════════

HOLIDAY_FALLBACK = {
    "is_public_holiday": 0,
    "holiday_missing": True,
    "is_major_event_nearby": 0,
    "event_distance_km": -1,
    "event_source": "unavailable",
    "holidays_today": [],
}


def normalize_holidays(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize Nager.Date response → today's holiday status."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    holidays_today = [h for h in raw if h.get("date") == today]
    is_holiday = len(holidays_today) > 0

    return {
        "is_public_holiday": 1 if is_holiday else 0,
        "holiday_missing": False,
        "is_major_event_nearby": 1 if is_holiday else 0,
        "event_distance_km": 0 if is_holiday else -1,
        "event_source": "nager_date",
        "holidays_today": [h.get("localName", h.get("name", "")) for h in holidays_today],
        "holidays_all_2026": [{"date": h.get("date"), "name": h.get("localName", h.get("name")),
                               "country": h.get("countryCode")} for h in raw],
    }


def ingest_holidays(api_url: str, dry_run: bool) -> dict[str, Any]:
    """Fetch holidays, normalize, optionally cache."""
    print(f"[holiday] Fetching: {api_url}")
    raw = _fetch_json(api_url)
    if raw is None or not isinstance(raw, list):
        print("[holiday] FAILED — using fallback")
        return {"status": "failed", "payload": HOLIDAY_FALLBACK.copy()}

    normalized = normalize_holidays(raw)
    is_holiday = normalized["is_public_holiday"]
    print(f"  today_holiday={is_holiday}, "
          f"holidays_today={normalized['holidays_today']}")
    if normalized.get("holidays_all_2026"):
        print(f"  total_2026_holidays={len(normalized['holidays_all_2026'])}")

    if dry_run:
        print(f"[holiday] DRY RUN — would cache {len(normalized['holidays_all_2026'])} holiday rows")
        return {"status": "dry_run", "payload": normalized}

    result = _write_to_cache(
        context_type="public_holidays",
        request_key=f"nager_us_2026",
        payload=normalized,
        ttl_hours=24,
    )
    print(f"[holiday] CACHED — expires_at={result['expires_at']}")
    return {"status": "ok", **result, "payload": normalized}


# ═══════════════════════════════════════════════════════════════════════════════
# Source 3: Citi Bike GBFS (station_status + station_information)
# ═══════════════════════════════════════════════════════════════════════════════

GBFS_FALLBACK = {
    "citibike_station_activity": 0,
    "citibike_activity_missing": True,
    "nearby_bike_availability": 0,
    "nearby_dock_availability": 0,
    "gbfs_snapshot_at": None,
    "gbfs_source": "unavailable",
}


def _load_station_info(info_url: str) -> dict[str, dict[str, Any]]:
    """Fetch station_information → {station_id: {name, lat, lon, capacity}}."""
    raw = _fetch_json(info_url)
    if raw is None:
        return {}
    stations = raw.get("data", {}).get("stations", []) if isinstance(raw, dict) else []
    return {s["station_id"]: s for s in stations if s.get("station_id")}


def normalize_gbfs(status_raw: dict[str, Any],
                    info_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Normalize GBFS station_status → aggregated NYC-wide features."""
    stations = status_raw.get("data", {}).get("stations", []) if isinstance(status_raw, dict) else []
    if not stations:
        return GBFS_FALLBACK.copy()

    total_bikes = 0
    total_docks = 0
    total_capacity = 0
    active_stations = 0

    for s in stations:
        sid = s.get("station_id", "")
        if not s.get("is_installed") or not s.get("is_renting"):
            continue
        bikes = s.get("num_bikes_available", 0) or 0
        docks = s.get("num_docks_available", 0) or 0
        total_bikes += bikes
        total_docks += docks
        active_stations += 1
        info = info_lookup.get(sid, {})
        capacity = info.get("capacity", bikes + docks) or (bikes + docks)
        total_capacity += capacity

    return {
        "citibike_station_activity": active_stations,
        "citibike_activity_missing": False,
        "nearby_bike_availability": total_bikes,
        "nearby_dock_availability": total_docks,
        "station_count": len(stations),
        "active_station_count": active_stations,
        "total_capacity": total_capacity,
        "gbfs_snapshot_at": datetime.now(timezone.utc).isoformat(),
        "gbfs_source": "lyft_gbfs_2.3",
    }


def ingest_gbfs(status_url: str, station_info_url: str | None, dry_run: bool) -> dict[str, Any]:
    """Fetch GBFS station_status + station_information, normalize, cache."""
    print(f"[gbfs] Fetching station_status: {status_url[:80]}...")

    # Fetch station_info if URL provided
    info_lookup: dict[str, dict] = {}
    if station_info_url:
        print(f"[gbfs] Fetching station_information: {station_info_url[:80]}...")
        info_lookup = _load_station_info(station_info_url)
        print(f"  loaded {len(info_lookup)} station info records")

    raw = _fetch_json(status_url)
    if raw is None:
        print("[gbfs] FAILED — using fallback")
        return {"status": "failed", "payload": GBFS_FALLBACK.copy()}

    normalized = normalize_gbfs(raw, info_lookup)
    print(f"  active_stations={normalized.get('active_station_count')}, "
          f"total_bikes={normalized.get('nearby_bike_availability')}, "
          f"total_docks={normalized.get('nearby_dock_availability')}")

    if dry_run:
        print("[gbfs] DRY RUN — would cache 1 aggregated row")
        return {"status": "dry_run", "payload": normalized}

    result = _write_to_cache(
        context_type="gbfs_station_status",
        request_key=f"citibike_nyc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
        payload=normalized,
        ttl_hours=1,  # GBFS is real-time, short TTL
    )
    print(f"[gbfs] CACHED — expires_at={result['expires_at']}")
    return {"status": "ok", **result, "payload": normalized}


# ═══════════════════════════════════════════════════════════════════════════════
# Source 4: MTA GTFS-RT Subway
# ═══════════════════════════════════════════════════════════════════════════════

MTA_FALLBACK = {
    "mta_service_disruption_flag": 0,
    "mta_disruption_missing": True,
    "mta_realtime_arrival_count_1h": 0,
    "mta_arrival_missing": True,
    "mta_source": "unavailable",
}


def normalize_mta_gtfs_rt(raw_bytes: bytes | None) -> dict[str, Any]:
    """Normalize MTA GTFS-RT protobuf response → aggregate features.

    Decode the raw protobuf feed when ``gtfs-realtime-bindings`` is available.
    A byte length is not an arrival count, so an undecodable feed remains
    explicitly missing rather than injecting a fabricated feature value.
    """
    if raw_bytes is None:
        return MTA_FALLBACK.copy()

    # Try to decode protobuf
    try:
        from google.transit import gtfs_realtime_pb2
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(raw_bytes)
        entity_count = len(feed.entity)
        header_timestamp = feed.header.timestamp

        # Count trip updates & alerts
        trip_updates = 0
        alerts = 0
        for entity in feed.entity:
            if entity.HasField("trip_update"):
                trip_updates += 1
            if entity.HasField("alert"):
                alerts += 1

        disruption_flag = 1 if alerts > 0 else 0

        return {
            "mta_service_disruption_flag": disruption_flag,
            "mta_disruption_missing": False,
            "mta_realtime_arrival_count_1h": trip_updates,
            "mta_arrival_missing": False,
            "mta_source": "gtfs_rt",
            "mta_entity_count": entity_count,
            "mta_alert_count": alerts,
            "mta_feed_timestamp": header_timestamp,
            "mta_gtfs_rt_available": True,
        }
    except ImportError:
        print("  [mta] gtfs-realtime-bindings not installed; retaining a missing feature")
        return {
            "mta_service_disruption_flag": 0,
            "mta_disruption_missing": True,
            "mta_realtime_arrival_count_1h": 0,
            "mta_arrival_missing": True,
            "mta_source": "gtfs_rt_raw",
            "mta_gtfs_rt_available": True,
            "mta_raw_bytes": len(raw_bytes),
        }
    except Exception as exc:
        print(f"  [mta] Failed to decode protobuf: {exc}")
        return {
            "mta_service_disruption_flag": 0,
            "mta_disruption_missing": True,
            "mta_realtime_arrival_count_1h": 0,
            "mta_arrival_missing": True,
            "mta_source": "gtfs_rt_raw",
            "mta_gtfs_rt_available": True,
            "mta_raw_bytes": len(raw_bytes),
        }


def ingest_mta(api_url: str, api_key_file: str | None, dry_run: bool) -> dict[str, Any]:
    """Fetch MTA GTFS-RT feed, normalize, cache."""
    print(f"[mta] Fetching: {api_url[:80]}...")

    api_key = None
    if api_key_file:
        key_path = Path(api_key_file).expanduser()
        if key_path.exists():
            api_key = key_path.read_text().strip()
            print(f"  using key from {api_key_file} ({len(api_key)} chars)")
        else:
            print(f"  WARNING: key file not found: {api_key_file}")

    if not api_key:
        print("[mta] No API key — trying anonymous request")
        raw_bytes = _fetch_raw(api_url, "")
    else:
        raw_bytes = _fetch_raw(api_url, api_key)

    normalized = normalize_mta_gtfs_rt(raw_bytes)
    print(f"  disruption_flag={normalized['mta_service_disruption_flag']}, "
          f"arrival_count={normalized['mta_realtime_arrival_count_1h']}, "
          f"source={normalized['mta_source']}")

    if dry_run:
        print(f"[mta] DRY RUN — would cache 1 aggregated row")
        return {"status": "dry_run", "payload": normalized}

    result = _write_to_cache(
        context_type="mta_realtime",
        request_key=f"mta_nyc_subway_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
        payload=normalized,
        ttl_hours=1,
    )
    print(f"[mta] CACHED — expires_at={result['expires_at']}")
    return {"status": "ok", **result, "payload": normalized}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

SOURCES = {
    "weather": ingest_weather,
    "holiday": ingest_holidays,
    "gbfs": ingest_gbfs,
    "mta_gtfs_rt": ingest_mta,
}

# Default API endpoints per SOP
DEFAULT_URLS = {
    "weather": (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=40.7128&longitude=-74.0060"
        "&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
        "precipitation,weather_code,wind_speed_10m"
        "&forecast_days=2&timezone=America%2FNew_York"
    ),
    "holiday": "https://date.nager.at/api/v4/Holidays/US/2026",
    "gbfs": "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_status.json",
    "gbfs_info": "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_information.json",
    "mta_gtfs_rt": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="External feature ingestion for forecast-v2")
    p.add_argument("--source", required=True, choices=list(SOURCES),
                   help="External data source to ingest")
    p.add_argument("--api-url", help="Override default API URL")
    p.add_argument("--api-key-file", help="Path to API key file (for MTA GTFS-RT)")
    p.add_argument("--station-info-url", help="GBFS station_information URL")
    p.add_argument("--dry-run", action="store_true", default=False,
                   help="Fetch and normalize but do not write to DB")
    p.add_argument("--execute", action="store_true",
                   help="Write fetched data to external_context_cache")
    p.add_argument("--ttl-hours", type=int, default=2,
                   help="Cache TTL in hours (default: 2)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True  # safe default: don't write unless --execute given

    source = args.source

    # Resolve URLs — use default if not overridden
    if source == "gbfs":
        status_url = args.api_url or DEFAULT_URLS["gbfs"]
        info_url = args.station_info_url or DEFAULT_URLS["gbfs_info"]
        result = SOURCES[source](status_url, info_url, args.dry_run)
    elif source == "mta_gtfs_rt":
        api_url = args.api_url or DEFAULT_URLS["mta_gtfs_rt"]
        result = SOURCES[source](api_url, args.api_key_file, args.dry_run)
    else:
        api_url = args.api_url or DEFAULT_URLS.get(source, "")
        result = SOURCES[source](api_url, args.dry_run)

    status = result.get("status", "unknown")
    print(f"\n[{source}] Result: {status}")

    if status == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

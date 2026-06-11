import json

import requests

from .db import etl_execute


WEATHER_API_BASE = "https://api.weather.gov"
WEATHER_HEADERS = {
    "User-Agent": "ClearPath/1.0 (clearpath-team6@example.com)",
    "Accept": "application/geo+json",
}
MANHATTAN_LAT = 40.758
MANHATTAN_LNG = -73.985


def test_weather_api():
    results = {}
    points_data = {}
    nearest = None
    endpoints = [
        ("base", f"{WEATHER_API_BASE}/"),
        ("points", f"{WEATHER_API_BASE}/points/{MANHATTAN_LAT},{MANHATTAN_LNG}"),
    ]
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=WEATHER_HEADERS, timeout=10)
            results[name] = {"status": response.status_code, "ok": response.ok}
            if name == "points" and response.ok:
                points_data = response.json()
        except requests.RequestException as error:
            results[name] = {"status": 0, "ok": False, "error": str(error)}

    properties = points_data.get("properties", {})
    for name, url in (
        ("forecast", properties.get("forecast")),
        ("stations", properties.get("observationStations")),
    ):
        if not url:
            results[name] = {"status": 0, "ok": False, "error": f"No {name} URL"}
            continue
        try:
            response = requests.get(url, headers=WEATHER_HEADERS, timeout=10)
            results[name] = {"status": response.status_code, "ok": response.ok}
            if name == "stations" and response.ok:
                stations = response.json().get("features", [])
                nearest = (
                    stations[0]["properties"]["stationIdentifier"] if stations else None
                )
        except requests.RequestException as error:
            results[name] = {"status": 0, "ok": False, "error": str(error)}

    if nearest:
        try:
            response = requests.get(
                f"{WEATHER_API_BASE}/stations/{nearest}/observations/latest",
                headers=WEATHER_HEADERS,
                timeout=10,
            )
            results["observation"] = {
                "status": response.status_code,
                "ok": response.ok,
            }
        except requests.RequestException as error:
            results["observation"] = {
                "status": 0,
                "ok": False,
                "error": str(error),
            }
    else:
        results["observation"] = {
            "status": 0,
            "ok": False,
            "error": "No station",
        }
    return results


def fetch_current_weather(station_url=None):
    station_url = station_url or f"{WEATHER_API_BASE}/stations/KNYC"
    response = requests.get(
        f"{station_url}/observations/latest",
        headers=WEATHER_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    properties = response.json().get("properties", {})
    return {
        "temperature_c": properties.get("temperature", {}).get("value"),
        "humidity_pct": properties.get("relativeHumidity", {}).get("value"),
        "wind_speed_kmh": properties.get("windSpeed", {}).get("value"),
        "description": properties.get("textDescription", ""),
    }


def classify_weather_risk(current):
    temperature = current.get("temperature_c")
    wind = current.get("wind_speed_kmh")
    description = (current.get("description") or "").lower()
    if temperature and temperature > 38:
        return "high"
    if wind and wind > 50:
        return "high"
    if any(
        word in description
        for word in ("heavy", "thunderstorm", "blizzard", "ice", "snow", "freezing")
    ):
        return "high"
    if temperature and temperature > 33:
        return "medium"
    if wind and wind > 30:
        return "medium"
    if any(
        word in description
        for word in ("rain", "showers", "drizzle", "fog", "mist", "windy")
    ):
        return "medium"
    return "low"


def etl_weather(conn):
    try:
        current = fetch_current_weather()
    except requests.RequestException:
        return {"imported": 0, "skipped": 1, "errors": 1}
    payload = {**current, "risk_level": classify_weather_risk(current)}
    statement = (
        "INSERT INTO external_context_cache "
        "(context_type, request_key, payload_json, valid_from, expires_at) "
        "VALUES (%s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 1 HOUR)) "
        "ON DUPLICATE KEY UPDATE payload_json = VALUES(payload_json), "
        "valid_from = NOW(), expires_at = DATE_ADD(NOW(), INTERVAL 1 HOUR)",
        (
            "weather_current",
            "weather:manhattan",
            json.dumps(payload, default=str),
        ),
    )
    success = etl_execute(
        conn, statement, source="weather", record_id="weather:manhattan"
    )
    return {
        "imported": int(success),
        "skipped": int(not success),
        "errors": int(not success),
    }

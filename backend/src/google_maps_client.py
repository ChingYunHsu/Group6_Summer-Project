"""Thin REST client for the Google Maps Directions API.

Uses `requests` directly (matching gemini_client.py's pattern) rather than
a full SDK dependency, since this is the only Google Maps call site in
the backend.
"""

import requests
from flask import current_app

DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"
REQUEST_TIMEOUT_SECONDS = 8


def _api_key() -> str:
    key = current_app.config.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")
    return key


def get_directions(origin: tuple, destination: tuple, mode: str) -> dict:
    """Raw Directions API response for one (origin, destination, mode).
    origin/destination are (latitude, longitude) tuples. mode is one of
    'transit', 'walking', 'driving'. Raises on any request failure or a
    non-OK API status — callers fall back to mock data."""
    response = requests.get(
        DIRECTIONS_API_URL,
        params={
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "mode": mode,
            "key": _api_key(),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Directions API returned status={data.get('status')!r}")

    return data


def decode_polyline(encoded: str) -> list:
    """Decode a Google encoded polyline string into [{latitude, longitude}, ...].

    Standard Google polyline algorithm — see
    https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    """
    points = []
    index = lat = lng = 0
    length = len(encoded)

    while index < length:
        for is_lat in (True, False):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if is_lat:
                lat += delta
            else:
                lng += delta
        points.append({"latitude": lat / 1e5, "longitude": lng / 1e5})

    return points

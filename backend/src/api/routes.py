import re
from copy import deepcopy

from flask import Blueprint, jsonify, request

import google_maps_client
from auth import require_api_key
from db import db_cursor
from mock_data import ROUTE_DETAIL, ROUTE_OPTIONS


bp = Blueprint("routes", __name__)

# Client-facing mode name -> Google Directions API mode param.
_MODE_TO_GOOGLE_MODE = {"walk": "walking", "transit": "transit", "drive": "driving"}

# Google's Directions API doesn't expose step-free/accessibility info
# directly (that would need a separate accessibility data source) — these
# mirror the same static per-mode labels the mock data already used, kept
# honest by documenting them as such rather than inventing per-request
# accessibility data we don't have.
_ACCESSIBILITY_MODE_BY_TRAVEL_MODE = {"transit": "step_free", "walk": "standard", "drive": "standard"}

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _get_venue_coordinates(venue_id: str):
    with db_cursor() as cursor:
        cursor.execute("SELECT latitude, longitude FROM venues WHERE venue_id = %s", (venue_id,))
        row = cursor.fetchone()
    if not row:
        return None
    return float(row["latitude"]), float(row["longitude"])


def _parse_origin(args):
    origin_lat = args.get("origin_lat", type=float)
    origin_lon = args.get("origin_lon", type=float)
    if origin_lat is None or origin_lon is None:
        return None
    return origin_lat, origin_lon


def _status_for_driving_leg(leg: dict) -> str:
    duration_s = leg.get("duration", {}).get("value")
    duration_in_traffic_s = leg.get("duration_in_traffic", {}).get("value")
    if duration_s and duration_in_traffic_s and duration_in_traffic_s > duration_s * 1.3:
        return "heavy_traffic"
    if duration_s and duration_in_traffic_s and duration_in_traffic_s > duration_s * 1.1:
        return "moderate_traffic"
    return "available"


def _summary_for_mode(travel_mode: str, origin: tuple, destination: tuple) -> dict:
    google_mode = _MODE_TO_GOOGLE_MODE[travel_mode]
    directions = google_maps_client.get_directions(origin, destination, google_mode)
    leg = directions["routes"][0]["legs"][0]

    duration_minutes = round(leg["duration"]["value"] / 60)
    status = _status_for_driving_leg(leg) if travel_mode == "drive" else "available"

    return {
        "duration_minutes": duration_minutes,
        "accessibility_mode": _ACCESSIBILITY_MODE_BY_TRAVEL_MODE[travel_mode],
        "status": status,
    }


def _get_route_options_from_maps(destination_venue_id: str, origin: tuple) -> dict:
    destination = _get_venue_coordinates(destination_venue_id)
    if destination is None:
        raise ValueError(f"Unknown venue: {destination_venue_id}")

    summary_by_mode = {}
    options = []
    for travel_mode in ("walk", "transit", "drive"):
        summary = _summary_for_mode(travel_mode, origin, destination)
        summary_by_mode[travel_mode] = summary
        options.append(
            {
                "mode": travel_mode,
                "duration_minutes": summary["duration_minutes"],
                "accessibility_mode": summary["accessibility_mode"],
                "status": summary["status"],
                "summary": f"Fastest {travel_mode} route",
            }
        )

    return {
        "origin_label": "Current Location",
        "destination_venue_id": destination_venue_id,
        "departure_time_label": "Leave Now",
        "summary_by_mode": summary_by_mode,
        "options": sorted(options, key=lambda option: option["duration_minutes"]),
    }


def _get_route_detail_from_maps(destination_venue_id: str, origin: tuple, travel_mode: str) -> dict:
    destination = _get_venue_coordinates(destination_venue_id)
    if destination is None:
        raise ValueError(f"Unknown venue: {destination_venue_id}")

    google_mode = _MODE_TO_GOOGLE_MODE.get(travel_mode, "transit")
    directions = google_maps_client.get_directions(origin, destination, google_mode)
    route = directions["routes"][0]
    leg = route["legs"][0]

    polyline_preview = google_maps_client.decode_polyline(route["overview_polyline"]["points"])
    steps = [
        _HTML_TAG_PATTERN.sub("", step["html_instructions"]).strip()
        for step in leg["steps"]
    ]

    return {
        "destination_venue_id": destination_venue_id,
        "polyline_preview": polyline_preview,
        "steps": steps,
        "start_navigation_label": "Start Navigation",
    }


@bp.get("/api/v1/routes/options")
@require_api_key
def get_route_options():
    destination_venue_id = request.args.get("destination_venue_id")
    origin = _parse_origin(request.args)

    if destination_venue_id and origin:
        try:
            return jsonify(_get_route_options_from_maps(destination_venue_id, origin))
        except Exception:
            pass  # Fallback to mock data below.

    return jsonify(deepcopy(ROUTE_OPTIONS))


@bp.get("/api/v1/routes/detail")
@require_api_key
def get_route_detail():
    destination_venue_id = request.args.get("destination_venue_id")
    origin = _parse_origin(request.args)
    travel_mode = request.args.get("mode", "transit")

    if destination_venue_id and origin:
        try:
            return jsonify(_get_route_detail_from_maps(destination_venue_id, origin, travel_mode))
        except Exception:
            pass  # Fallback to mock data below.

    return jsonify(deepcopy(ROUTE_DETAIL))

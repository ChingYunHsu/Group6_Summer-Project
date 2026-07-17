import json as _json
import math
import os

import pymysql
from flask import Blueprint, jsonify, request

from mock_data import INSIGHTS_DASHBOARD


bp = Blueprint("insights", __name__)

FASTEST_HUBS_LIMIT = 10
WALKING_SPEED_KM_PER_HOUR = 5.0


def _get_db_conn():
    """Create MySQL connection for area-aggregation queries (per-request)."""
    return pymysql.connect(
        host=os.environ.get('CLEARPATH_DB_HOST', '127.0.0.1'),
        port=int(os.environ.get('CLEARPATH_DB_PORT', '3306')),
        user=os.environ.get('CLEARPATH_DB_USER', 'clearpath_app'),
        password=os.environ.get('CLEARPATH_DB_PASSWORD', 'clearpath_app'),
        database=os.environ.get('CLEARPATH_DB_NAME', 'clearpath'),
        charset='utf8mb4',
    )


def _parse_json_list(value) -> list:
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except ValueError:
            return []
    return value or []


def _flow_status(score) -> str:
    if score is None:
        return "NO DATA"
    if score < 50:
        return "OPTIMAL FLOW"
    if score < 75:
        return "MODERATE"
    return "DIVERTING"


def _get_default_district(cursor):
    """Pick a district to report on when the caller didn't specify one."""
    cursor.execute("SELECT DISTINCT district FROM venues")
    row = cursor.fetchone()
    return row[0] if row else None


# ── D3.5: real-time density ──────────────────────────────────────────────

def _real_time_density(cursor, district: str) -> dict:
    """Average current busyness score across every venue in `district`."""
    cursor.execute(
        "SELECT bs.score, bs.estimated_wait_minutes "
        "FROM busyness_scores bs "
        "JOIN venues v ON v.venue_id = bs.venue_id "
        "WHERE v.district = %s",
        (district,),
    )
    rows = cursor.fetchall()

    if not rows:
        return {"percent": 0, "trend": "no data", "trend_label": "No data available"}

    scores = [row[0] for row in rows]
    percent = round(sum(scores) / len(scores))
    return {"percent": percent, "trend": "stable", "trend_label": "Stable"}


# ── D3.5: best travel window ─────────────────────────────────────────────

def _best_travel_window(cursor, district: str) -> dict:
    """Pick the 2-hour forecast window with the lowest average busyness
    across every venue in `district`, averaged hour-by-hour cross-venue."""
    cursor.execute(
        "SELECT bf.forecast_for, AVG(bf.predicted_score) "
        "FROM busyness_forecasts bf "
        "JOIN venues v ON v.venue_id = bf.venue_id "
        "WHERE v.district = %s "
        "GROUP BY bf.forecast_for "
        "ORDER BY bf.forecast_for "
        "LIMIT 12",
        (district,),
    )
    rows = cursor.fetchall()

    if not rows:
        return {"start_time": None, "end_time": None, "cta_label": "Check back soon"}

    if len(rows) == 1:
        hour, _score = rows[0]
        return {"start_time": hour.isoformat(), "end_time": hour.isoformat(), "cta_label": "Plan Route"}

    best_start_idx = min(
        range(len(rows) - 1),
        key=lambda i: rows[i][1] + rows[i + 1][1],
    )
    start_hour, _ = rows[best_start_idx]
    end_hour, _ = rows[best_start_idx + 1]
    return {"start_time": start_hour.isoformat(), "end_time": end_hour.isoformat(), "cta_label": "Plan Route"}


# ── D3.5: fastest hubs ────────────────────────────────────────────────────

def _fastest_hubs(cursor, district: str, limit: int = FASTEST_HUBS_LIMIT) -> list:
    """Rank venues in `district` by current busyness (lowest first), then
    by wait time; venues with no live score sort last."""
    cursor.execute(
        "SELECT v.venue_id, v.name, v.language_tags, v.accessible_status, "
        "bs.score, bs.level, bs.estimated_wait_minutes "
        "FROM venues v "
        "LEFT JOIN busyness_scores bs ON bs.venue_id = v.venue_id "
        "WHERE v.district = %s "
        "ORDER BY (bs.score IS NULL), bs.score, bs.estimated_wait_minutes "
        "LIMIT %s",
        (district, limit),
    )
    rows = cursor.fetchall()

    hubs = []
    for venue_id, name, language_tags, accessible_status, score, level, wait_minutes in rows:
        hubs.append(
            {
                "venue_id": venue_id,
                "venue_name": name,
                "flow_status": _flow_status(score),
                "busyness_score": score,
                "busyness_level": level,
                "wait_minutes": wait_minutes,
                "language_tags": _parse_json_list(language_tags),
                "accessible_status": accessible_status,
            }
        )
    return hubs


# ── D3.5/D3.7: prediction series ─────────────────────────────────────────

def _prediction_series(cursor, district: str) -> list:
    """Hour-by-hour predicted busyness, averaged across every venue in
    `district`, rounded to whole percent."""
    cursor.execute(
        "SELECT bf.forecast_for, AVG(bf.predicted_score) "
        "FROM busyness_forecasts bf "
        "JOIN venues v ON v.venue_id = bf.venue_id "
        "WHERE v.district = %s "
        "GROUP BY bf.forecast_for "
        "ORDER BY bf.forecast_for "
        "LIMIT 12",
        (district,),
    )
    rows = cursor.fetchall()
    return [round(avg_score) for _hour, avg_score in rows]


def _quick_triage(hubs: list) -> dict:
    """Surface the single fastest (lowest-wait) hub as the "go here now"
    triage suggestion. Venues with no live wait data are never picked over
    one that has data."""
    scored = [hub for hub in hubs if hub.get("wait_minutes") is not None]
    if not scored:
        return {"wait_minutes": 0, "label": "No data available", "venue_name": None}

    best = min(scored, key=lambda hub: hub["wait_minutes"])
    return {
        "wait_minutes": best["wait_minutes"],
        "label": best["venue_name"],
        "venue_name": best["venue_name"],
    }


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _travel_minutes_by_venue(cursor, venue_ids: list, origin_lat, origin_lon) -> dict:
    """Straight-line walking-time estimate from (origin_lat, origin_lon) to
    each venue, at WALKING_SPEED_KM_PER_HOUR. This is a placeholder pending
    the Data Lead's real routing/travel-time pipeline output (e.g. Google
    Maps Directions) — straight-line distance, not actual walkable route
    distance, but gives an honest non-fabricated integer rather than a
    made-up constant."""
    if origin_lat is None or origin_lon is None or not venue_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(venue_ids))
    cursor.execute(
        f"SELECT venue_id, latitude, longitude FROM venues WHERE venue_id IN ({placeholders})",
        tuple(venue_ids),
    )
    rows = cursor.fetchall()

    minutes_by_venue = {}
    for venue_id, lat, lon in rows:
        if lat is None or lon is None:
            continue
        distance_km = _haversine_km(float(origin_lat), float(origin_lon), float(lat), float(lon))
        minutes_by_venue[venue_id] = round(distance_km / WALKING_SPEED_KM_PER_HOUR * 60)
    return minutes_by_venue


def _get_insights_from_db(district_param, origin_lat=None, origin_lon=None):
    conn = _get_db_conn()
    try:
        with conn.cursor() as cursor:
            district = district_param or _get_default_district(cursor)
            if not district:
                raise RuntimeError("no districts available in venues table")

            density = _real_time_density(cursor, district)
            travel_window = _best_travel_window(cursor, district)
            hubs = _fastest_hubs(cursor, district)
            prediction_series = _prediction_series(cursor, district)
            travel_minutes_by_venue = _travel_minutes_by_venue(
                cursor, [hub["venue_id"] for hub in hubs], origin_lat, origin_lon
            )
    finally:
        conn.close()

    has_data = (
        density["trend"] != "no data"
        or bool(prediction_series)
        or any(hub["busyness_score"] is not None for hub in hubs)
    )

    return {
        "district": district,
        "data_mode": "db" if has_data else "no_data",
        "real_time_density": density,
        "quick_triage": _quick_triage(hubs),
        "best_travel_window": travel_window,
        "chart_mode": "live",
        "prediction_series": prediction_series,
        "history_series_7d": [],
        "fastest_hubs": [
            {
                "rank": index + 1,
                "venue_id": hub["venue_id"],
                "clinic_name": hub["venue_name"],
                "venue_name": hub["venue_name"],
                "capacity_label": hub["flow_status"],
                "flow_status": hub["flow_status"],
                "travel_minutes": travel_minutes_by_venue.get(hub["venue_id"], 0),
                "wait_minutes": hub["wait_minutes"],
                "languages": hub["language_tags"],
                "language_flags": hub["language_tags"],
            }
            for index, hub in enumerate(hubs)
        ],
    }


@bp.get("/api/v1/insights")
def get_insights():
    district_param = request.args.get("district")
    origin_lat = request.args.get("lat", type=float)
    origin_lon = request.args.get("lon", type=float)

    try:
        return jsonify(_get_insights_from_db(district_param, origin_lat, origin_lon))
    except Exception:
        pass  # Fallback to mock data below.

    district = district_param or INSIGHTS_DASHBOARD.get("district", "all")
    dashboard = INSIGHTS_DASHBOARD.copy()

    response = {
        "district": district,
        "data_mode": "mock",
        "real_time_density": {
            "percent": dashboard["real_time_density"]["percent"],
            "trend": dashboard["real_time_density"].get("trend_label", dashboard["real_time_density"].get("trend", "")),
            "trend_label": dashboard["real_time_density"].get("trend_label"),
        },
        "quick_triage": {
            "wait_minutes": dashboard["quick_triage"]["wait_minutes"],
            "label": dashboard["quick_triage"].get("venue_name", dashboard["quick_triage"].get("label", "")),
            "venue_name": dashboard["quick_triage"].get("venue_name"),
        },
        "best_travel_window": {
            "start_time": dashboard["best_travel_window"].get("start_time", dashboard["best_travel_window"].get("start", "")),
            "end_time": dashboard["best_travel_window"].get("end_time", dashboard["best_travel_window"].get("end", "")),
            "start": dashboard["best_travel_window"].get("start"),
            "end": dashboard["best_travel_window"].get("end"),
            "cta_label": dashboard["best_travel_window"].get("cta_label"),
        },
        "chart_mode": dashboard.get("chart_mode"),
        "prediction_series": dashboard.get("prediction_series", []),
        "history_series_7d": dashboard.get("history_series_7d", []),
        "fastest_hubs": [
            {
                "rank": hub.get("rank"),
                "venue_id": hub.get("venue_id"),
                "clinic_name": hub.get("venue_name"),
                "venue_name": hub.get("venue_name"),
                "capacity_label": hub.get("flow_status"),
                "flow_status": hub.get("flow_status"),
                "travel_minutes": hub.get("travel_minutes"),
                "wait_minutes": hub.get("wait_minutes"),
                "languages": hub.get("language_flags", []),
                "language_flags": hub.get("language_flags", []),
            }
            for hub in dashboard.get("fastest_hubs", [])
        ],
    }

    return jsonify(response)

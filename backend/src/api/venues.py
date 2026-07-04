import json as _json
import os
import re
from copy import deepcopy
from datetime import datetime

import pymysql
from flask import Blueprint, jsonify, request

from auth import require_api_key
from db import db_cursor
from mock_data import VENUE_BUSYNESS, VENUE_FORECASTS, VENUES


bp = Blueprint("venues", __name__)

# Matches free-text supported_services entries like "French Help Available"
# or "Bilingual Staff (Spanish)" so the client always gets an explicit,
# structured badge list instead of having to pattern-match itself.
_BILINGUAL_BADGE_PATTERN = re.compile(
    r"(?P<language>[A-Za-z]+)\s+Help Available|Bilingual Staff \((?P<language_paren>[A-Za-z]+)\)"
)


def _extract_bilingual_badges(supported_services: list) -> list:
    """Pull structural bilingual service badges out of the free-text
    supported_services list so the frontend never has to parse strings to
    know which languages have live human/chatbot support."""
    badges = []
    for entry in supported_services or []:
        match = _BILINGUAL_BADGE_PATTERN.match(entry)
        if not match:
            continue
        language = match.group("language") or match.group("language_paren")
        badges.append({"label": entry, "language": language})
    return badges


def _row_to_venue(row: dict) -> dict:
    """Normalize a `venues` table row into the API's venue representation,
    parsing JSON columns and deriving the bilingual badge list."""
    venue = dict(row)
    for json_field in ("language_tags", "accessibility_features", "supported_services", "opening_hours_structured"):
        raw = venue.get(json_field)
        if isinstance(raw, str):
            venue[json_field] = _json.loads(raw)
    venue["language_tags"] = venue.get("language_tags") or []
    venue["supported_services"] = venue.get("supported_services") or []
    venue["bilingual_service_badges"] = _extract_bilingual_badges(venue["supported_services"])
    venue["open_now"] = bool(venue.get("open_now"))
    for bool_field in ("chatbot_enabled", "wheelchair_friendly", "step_free_route", "accessible_toilet"):
        if bool_field in venue:
            venue[bool_field] = bool(venue[bool_field])
    if venue.get("created_at") is not None and hasattr(venue["created_at"], "isoformat"):
        venue["created_at"] = venue["created_at"].isoformat()
    return venue


# ── DB helpers ────────────────────────────────────────────────

def _get_db_conn():
    """Create MySQL connection for busyness queries (per-request)."""
    return pymysql.connect(
        host=os.environ.get('CLEARPATH_DB_HOST', '127.0.0.1'),
        port=int(os.environ.get('CLEARPATH_DB_PORT', '3306')),
        user=os.environ.get('CLEARPATH_DB_USER', 'clearpath_app'),
        password=os.environ.get('CLEARPATH_DB_PASSWORD', 'clearpath_app'),
        database=os.environ.get('CLEARPATH_DB_NAME', 'clearpath'),
        charset='utf8mb4',
    )


def _level_to_color(level: str) -> str:
    """Map busyness level to display color (per OpenAPI spec / F-01)."""
    return {
        'quiet': 'green',
        'moderate': 'yellow',
        'busy': 'red',
        'no_data': '#2563EB',  # blue — no live telemetry available
    }.get(level, '#2563EB')


VALID_VENUE_TYPES = {"hospital", "clinic", "pharmacy", "urgent_care", "mental_health", "shelter"}


def _parse_venue_query_matrix(args):
    """Parse the URL matrix query params shared by the venues list endpoint."""
    languages_param = args.get("languages", "")
    accessible_param = args.get("accessible", "")
    open_now_param = args.get("open_now", "")
    venue_type_param = args.get("venue_type", "")

    return {
        "languages": [language.strip().upper() for language in languages_param.split(",") if language.strip()],
        "accessible": accessible_param.lower() if accessible_param else "",
        "open_now": open_now_param.lower() if open_now_param else "",
        "venue_type": venue_type_param.strip().lower() if venue_type_param else "",
    }


def _list_venues_from_db(query):
    where_clauses = []
    params = []

    if query["accessible"] in {"true", "false"}:
        where_clauses.append("accessible_status " + ("= %s" if query["accessible"] == "true" else "!= %s"))
        params.append("full_access")

    if query["open_now"] in {"true", "false"}:
        where_clauses.append("open_now = %s")
        params.append(1 if query["open_now"] == "true" else 0)

    if query["venue_type"]:
        if query["venue_type"] not in VALID_VENUE_TYPES:
            raise ValueError(f"Unknown venue type: {query['venue_type']}")
        where_clauses.append("venue_type = %s")
        params.append(query["venue_type"])

    sql = "SELECT * FROM venues"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    with db_cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    venues = [_row_to_venue(row) for row in rows]

    # language_tags filtering happens in Python since it's a JSON array column.
    if query["languages"]:
        venues = [
            venue for venue in venues
            if any(language in venue["language_tags"] for language in query["languages"])
        ]

    return venues


@bp.get("/api/v1/venues")
@require_api_key
def list_venues():
    query = _parse_venue_query_matrix(request.args)

    if query["venue_type"] and query["venue_type"] not in VALID_VENUE_TYPES:
        return jsonify({"error": f"Unknown venue type: {query['venue_type']}"}), 400

    try:
        filtered_items = _list_venues_from_db(query)
        return jsonify({"count": len(filtered_items), "items": filtered_items})
    except Exception:
        pass  # Fallback to mock data below.

    filtered_items = VENUES

    if query["languages"]:
        filtered_items = [
            venue for venue in filtered_items
            if any(language in venue["language_tags"] for language in query["languages"])
        ]

    if query["accessible"] in {"true", "false"}:
        if query["accessible"] == "true":
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] == "full_access"]
        else:
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] != "full_access"]

    if query["open_now"] in {"true", "false"}:
        expected_open = query["open_now"] == "true"
        filtered_items = [venue for venue in filtered_items if venue["open_now"] == expected_open]

    if query["venue_type"]:
        filtered_items = [venue for venue in filtered_items if venue.get("venue_type") == query["venue_type"]]

    return jsonify({"count": len(filtered_items), "items": filtered_items})


@bp.get("/api/v1/venues/<venue_id>")
@require_api_key
def get_venue(venue_id: str):
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT * FROM venues WHERE venue_id = %s", (venue_id,))
            row = cursor.fetchone()
        if row:
            return jsonify(_row_to_venue(row))
    except Exception:
        pass  # Fallback to mock data below.

    venue = next((venue for venue in VENUES if venue["venue_id"] == venue_id), None)
    if not venue:
        return jsonify({"error": "Venue not found."}), 404
    return jsonify(venue)


@bp.get("/api/v1/venues/<venue_id>/busyness")
@require_api_key
def get_venue_busyness(venue_id: str):
    """Return current busyness for a venue.

    Reads from busyness_scores table; falls back to mock data if DB
    is unavailable or has no matching record.
    """
    # --- Try DB first ---
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                now = datetime.now()
                cur.execute(
                    "SELECT score, level, estimated_wait_minutes, created_at, forecast_end_time "
                    "FROM busyness_scores "
                    "WHERE venue_id = %s "
                    "  AND forecast_start_time <= %s "
                    "  AND forecast_end_time > %s "
                    "ORDER BY forecast_start_time DESC LIMIT 1",
                    (venue_id, now, now),
                )
                row = cur.fetchone()
                if row:
                    score, level, wait_min, created_at, expires_at = row
                    return jsonify({
                        "venue_id": venue_id,
                        "busyness": {
                            "busyness_score": score,
                            "busyness_status": level,
                            "busyness_color": _level_to_color(level),
                            "is_future_time_query": False,
                            "data_mode": "live",
                            "estimated_wait_minutes": wait_min,
                            "updated_at": (
                                created_at.isoformat() + "Z" if created_at else None
                            ),
                            "expires_at": (
                                expires_at.isoformat() + "Z" if expires_at else None
                            ),
                        },
                    })
        finally:
            conn.close()
    except Exception:
        pass  # Fallback to mock

    # --- Fallback to mock data ---
    entry = VENUE_BUSYNESS.get(venue_id)
    if not entry:
        return jsonify({"error": "Venue not found."}), 404

    response = deepcopy(entry)
    query_time = request.args.get("query_time")

    if query_time:
        response["busyness"]["is_future_time_query"] = True
        response["busyness"]["busyness_color"] = "#2563EB"
        response["busyness"]["data_mode"] = "predicted"

    return jsonify(response)


@bp.get("/api/v1/venues/<venue_id>/busyness/forecast")
@require_api_key
def get_venue_busyness_forecast(venue_id: str):
    """Return 12-hour busyness forecast for a venue.

    Reads forecast_1h JSON from busyness_scores table; falls back to mock.
    """
    # --- Try DB first ---
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT forecast_1h FROM busyness_scores "
                    "WHERE venue_id = %s AND forecast_1h IS NOT NULL "
                    "ORDER BY forecast_start_time DESC LIMIT 1",
                    (venue_id,),
                )
                row = cur.fetchone()
                if row:
                    forecast_raw = row[0]
                    forecast_list = (
                        _json.loads(forecast_raw)
                        if isinstance(forecast_raw, str)
                        else forecast_raw
                    )
                    # Find best time to go (lowest percent)
                    best = min(forecast_list, key=lambda x: x.get("percent", 100))
                    return jsonify({
                        "venue_id": venue_id,
                        "forecast": forecast_list,
                        "best_time_to_go_today": {
                            "offset_hours": best["offset_hours"],
                            "percent": best["percent"],
                            "label": (
                                "Now"
                                if best["offset_hours"] == 0
                                else f"In {best['offset_hours']} hours"
                            ),
                        },
                    })
        finally:
            conn.close()
    except Exception:
        pass  # Fallback to mock

    # --- Fallback to mock data ---
    forecast = VENUE_FORECASTS.get(venue_id)
    if not forecast:
        return jsonify({"error": "Venue not found."}), 404

    return jsonify(deepcopy(forecast))

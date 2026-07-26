import json as _json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import pymysql
from flask import Blueprint, jsonify, request

from auth import require_api_key
from db import db_cursor
from mock_data import VENUES
from response_cache import get_cached, set_cached


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
    venue["language_tags"] = [str(language).upper() for language in (venue.get("language_tags") or [])]
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


def _get_external_feature_status() -> dict:
    """Return a summary of external feature sources from external_context_cache.

    Queries the most recent entry per context_type so the forecast response can
    expose whether weather/holiday/GBFS/MTA data fed into the forecast model.
    """
    status: dict[str, Any] = {"sources": {}, "checked_at": None}
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT context_type, request_key, valid_from, expires_at "
                    "FROM external_context_cache "
                    "WHERE expires_at >= NOW() "
                    "ORDER BY context_type, valid_from DESC"
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        checked_at = datetime.now(timezone.utc).isoformat()
        status["checked_at"] = checked_at.replace("+00:00", "Z")

        seen: set[str] = set()
        for ctx_type, req_key, valid_from, expires_at in rows:
            if ctx_type in seen:
                continue
            seen.add(ctx_type)
            vf = valid_from
            if vf and vf.tzinfo is None:
                vf = vf.replace(tzinfo=timezone.utc)
            ex = expires_at
            if ex and ex.tzinfo is None:
                ex = ex.replace(tzinfo=timezone.utc)
            status["sources"][ctx_type] = {
                "available": True,
                "request_key": req_key,
                "valid_from": vf.isoformat() if vf else None,
                "expires_at": ex.isoformat() if ex else None,
            }
    except Exception:
        status["status"] = "unavailable"
        return status

    if not seen:
        status["status"] = "no_active_cache"
    else:
        status["status"] = "ok"
    return status


def _level_to_color(level: str) -> str:
    """Map busyness level to display color (per OpenAPI spec / F-01)."""
    return {
        'quiet': 'green',
        'moderate': 'yellow',
        'busy': 'red',
        'no_data': '#2563EB',  # blue — no live telemetry available
    }.get(level, '#2563EB')


# Matches the venue_type ENUM in 001_clearpath_schema.sql exactly. Only
# clinic/pharmacy/emergencyasset/hospital/restroom have seeded data today
# (005_seed_venues.sql) but healthcare/dentist/laboratory are valid enum
# values too, so filtering by them should never 400 — it should just
# legitimately return zero results until those are seeded.
VALID_VENUE_TYPES = {
    "restroom",
    "healthcare",
    "emergencyasset",
    "clinic",
    "pharmacy",
    "hospital",
    "dentist",
    "laboratory",
}

# Only medical venue types may show V2 busyness predictions.
# AEDs (emergencyasset) and restrooms always render the unavailable state,
# even though historical V2 rows exist for them from before this rule.
V2_PREDICTABLE_VENUE_TYPES = {
    "healthcare", "clinic", "hospital", "pharmacy", "dentist", "laboratory",
}


def _get_venue_type(cursor, venue_id: str):
    """None means the venue doesn't exist at all (→ 404); otherwise the raw
    venue_type, which the caller checks against V2_PREDICTABLE_VENUE_TYPES."""
    cursor.execute("SELECT venue_type FROM venues WHERE venue_id = %s", (venue_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def _unavailable_forecast(venue_id: str) -> dict:
    return {
        "venue_id": venue_id,
        "data_mode": "unavailable",
        "forecast_source": "busyness_forecasts",
        "unavailable_reason": "no_v2_forecast",
        "forecast": [],
    }


def _unavailable_busyness(venue_id: str) -> dict:
    return {
        "venue_id": venue_id,
        "busyness": {
            "busyness_score": None,
            "busyness_status": "no_data",
            "busyness_color": _level_to_color("no_data"),
            "is_future_time_query": False,
            "data_mode": "unavailable",
            "forecast_source": "busyness_forecasts",
            "unavailable_reason": "no_v2_forecast",
            "estimated_wait_minutes": None,
            "updated_at": None,
            "expires_at": None,
        },
    }


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

    if query["accessible"] == "true":
        where_clauses.append("accessible_status = %s")
        params.append("full_access")
    elif query["accessible"] == "false":
        # Unknown is not evidence of inaccessibility and must not be returned
        # as a negative accessibility result.
        where_clauses.append("accessible_status IN (%s, %s, %s)")
        params.extend(["none", "partial", "step_free_route_only"])

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
            filtered_items = [
                venue for venue in filtered_items
                if venue["accessible_status"] in {"none", "partial", "step_free_route_only"}
            ]

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
    """Return current busyness for a venue, resolved from the nearest future
    V2 forecast point. Only medical venue types are V2-predictable;
    live-telemetry and legacy traffic-baseline data are
    no longer part of this public contract, so an ineligible venue type, or
    an eligible venue with no current V2 rows, returns the unavailable
    payload rather than falling back to those older sources."""
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                venue_type = _get_venue_type(cur, venue_id)
                if venue_type is None:
                    return jsonify({"error": "Venue not found."}), 404

                if venue_type not in V2_PREDICTABLE_VENUE_TYPES:
                    return jsonify(_unavailable_busyness(venue_id))

                cur.execute(
                    "SELECT predicted_score, predicted_level, estimated_wait_minutes, "
                    "forecast_for, generated_at "
                    "FROM busyness_forecasts "
                    "WHERE venue_id = %s "
                    "  AND model_version = 'forecast-v2' "
                    "  AND forecast_for >= UTC_TIMESTAMP() "
                    "  AND generated_at = ("
                    "    SELECT MAX(generated_at) FROM busyness_forecasts "
                    "    WHERE venue_id = %s AND model_version = 'forecast-v2'"
                    "  ) "
                    "ORDER BY forecast_for ASC LIMIT 1",
                    (venue_id, venue_id),
                )
                row = cur.fetchone()
        finally:
            conn.close()
    except Exception:
        # A DB outage leaves V2 data unresolvable either way — the caller
        # must not be told the venue is unavailable "because no live data
        # exists" vs. "because the DB is down", but it also must never get
        # a legacy/mock value presented as a real prediction.
        return jsonify(_unavailable_busyness(venue_id))

    if not row:
        return jsonify(_unavailable_busyness(venue_id))

    score, level, wait_min, forecast_for, generated_at = row
    return jsonify({
        "venue_id": venue_id,
        "busyness": {
            "busyness_score": score,
            "busyness_status": level,
            "busyness_color": _level_to_color(level),
            "is_future_time_query": False,
            "data_mode": "forecast",
            "forecast_source": "busyness_forecasts",
            "estimated_wait_minutes": wait_min,
            "updated_at": (
                generated_at.isoformat() + "Z" if generated_at else None
            ),
            "expires_at": (
                forecast_for.isoformat() + "Z" if forecast_for else None
            ),
        },
    })


FORECAST_CACHE_TTL_SECONDS = 300  # 5 minutes


def _forecast_cache_key(venue_id: str) -> str:
    return f"forecast:v1:{venue_id}"


def _compute_venue_busyness_forecast(venue_id: str):
    """Return the 12-hour V2 busyness forecast for a venue.

    Returns None only when the venue itself doesn't exist (→ 404). Per
    Only medical venue types are V2-predictable, and only forecast-v2 rows
    for future timestamps from each venue's latest
    generation batch are ever surfaced — no traffic-baseline, legacy
    forecast_1h, or mock fallback. Every other outcome (ineligible type, no
    current V2 rows, DB unreachable) returns the unavailable payload."""
    now = datetime.now(timezone.utc)

    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                venue_type = _get_venue_type(cur, venue_id)
                if venue_type is None:
                    return None

                if venue_type not in V2_PREDICTABLE_VENUE_TYPES:
                    return _unavailable_forecast(venue_id)

                cur.execute(
                    "SELECT forecast_for, predicted_score, predicted_level, "
                    "estimated_wait_minutes, model_version, generated_at "
                    "FROM busyness_forecasts "
                    "WHERE venue_id = %s "
                    "  AND model_version = 'forecast-v2' "
                    "  AND forecast_for >= UTC_TIMESTAMP() "
                    "  AND generated_at = ("
                    "    SELECT MAX(generated_at) FROM busyness_forecasts "
                    "    WHERE venue_id = %s AND model_version = 'forecast-v2'"
                    "  ) "
                    "ORDER BY forecast_for ASC LIMIT 12",
                    (venue_id, venue_id),
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception:
        # A DB outage leaves V2 data unresolvable — see get_venue_busyness's
        # equivalent note; never surface a legacy/mock value instead.
        return _unavailable_forecast(venue_id)

    if not rows:
        return _unavailable_forecast(venue_id)

    forecast_list = []
    model_version = None
    generated_at = None
    for (forecast_for, score, level, wait_minutes, mv, gen) in rows:
        if model_version is None:
            model_version = mv
        if generated_at is None:
            generated_at = gen
        # forecast_for is naive (MySQL DATETIME); treat as UTC.
        ff = forecast_for
        if ff.tzinfo is None:
            ff = ff.replace(tzinfo=timezone.utc)
        # offset_hours is hours-from-now (wall clock at request time),
        # not hours-from-the-first-row — so it matches how far ahead
        # the client actually has to wait, e.g. row 9 of 12 is "in 9
        # hours" even if row 1 wasn't exactly "now".
        offset_hours = max(0, round((ff - now).total_seconds() / 3600))
        forecast_list.append({
            "offset_hours": offset_hours,
            "percent": int(score),
            "level": level,
            "forecast_for": ff.isoformat(),
            "estimated_wait_minutes": int(wait_minutes) if wait_minutes is not None else None,
        })

    best = min(forecast_list, key=lambda x: x["percent"])
    response = {
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
        "data_mode": "forecast",
        "forecast_source": "busyness_forecasts",
        "model_version": model_version,
        "feature_snapshot_at": (
            generated_at.isoformat() + "Z"
            if generated_at and generated_at.tzinfo is None
            else generated_at.isoformat()
            if generated_at
            else None
        ),
    }
    # --- Attach external_feature_status from context cache ---
    try:
        response["external_feature_status"] = _get_external_feature_status()
    except Exception:
        response["external_feature_status"] = {"status": "unavailable"}
    return response


@bp.get("/api/v1/venues/<venue_id>/busyness/forecast")
@require_api_key
def get_venue_busyness_forecast(venue_id: str):
    """Serve the 12-hour busyness forecast, backed by a 5-minute server-side
    cache so repeated requests for the same venue don't re-hit MySQL/the ML
    forecast tables on every call. Cache expiry is transparent to clients —
    same response shape either way, just served faster on a hit; no new
    fields, no client-visible cache-control contract to manage."""
    cache_key = _forecast_cache_key(venue_id)
    cached = get_cached(cache_key)
    if cached is not None:
        return jsonify(cached)

    payload = _compute_venue_busyness_forecast(venue_id)
    if payload is None:
        return jsonify({"error": "Venue not found."}), 404

    set_cached(cache_key, payload, FORECAST_CACHE_TTL_SECONDS)
    return jsonify(payload)

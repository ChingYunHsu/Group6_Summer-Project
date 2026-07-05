import json as _json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pymysql
from flask import Blueprint, jsonify, request

from auth import require_api_key
from mock_data import VENUE_BUSYNESS, VENUE_FORECASTS, VENUES


bp = Blueprint("venues", __name__)


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


@bp.get("/api/v1/venues")
@require_api_key
def list_venues():
    languages_param = request.args.get("languages", "")
    accessible_param = request.args.get("accessible", "")
    open_now_param = request.args.get("open_now", "")

    selected_languages = [language.strip().upper() for language in languages_param.split(",") if language.strip()]
    accessible_filter = accessible_param.lower() if accessible_param else ""
    open_now_filter = open_now_param.lower() if open_now_param else ""

    filtered_items = VENUES

    if selected_languages:
        filtered_items = [
            venue for venue in filtered_items if any(language in venue["language_tags"] for language in selected_languages)
        ]

    if accessible_filter in {"true", "false"}:
        if accessible_filter == "true":
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] == "full_access"]
        else:
            filtered_items = [venue for venue in filtered_items if venue["accessible_status"] != "full_access"]

    if open_now_filter in {"true", "false"}:
        expected_open = open_now_filter == "true"
        filtered_items = [venue for venue in filtered_items if venue["open_now"] == expected_open]

    return jsonify({"count": len(filtered_items), "items": filtered_items})


@bp.get("/api/v1/venues/<venue_id>")
@require_api_key
def get_venue(venue_id: str):
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

    Primary source: the `busyness_forecasts` table (12h row series written by
    the ML pipeline). Migration fallback: the legacy `busyness_scores.forecast_1h`
    JSON blob. Final fallback: mock data.

    `data_mode` / `forecast_source` make the data lineage observable so the
    frontend (and SOP D3.5 aggregation) can tell live-ML data from mock:
      - data_mode="forecast",  forecast_source="busyness_forecasts"
      - data_mode="predicted", forecast_source="busyness_scores.forecast_1h"
      - data_mode="mock",      forecast_source="mock_data"
    """
    now = datetime.now(timezone.utc)

    # --- Primary: busyness_forecasts (12h row series) ---
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT forecast_for, predicted_score, predicted_level, "
                    "estimated_wait_minutes, model_version, generated_at "
                    "FROM busyness_forecasts "
                    "WHERE venue_id = %s AND forecast_for >= NOW() "
                    "ORDER BY forecast_for ASC LIMIT 12",
                    (venue_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        if rows:
            forecast_list = []
            for (forecast_for, score, level, wait_minutes, _mv, _gen) in rows:
                # forecast_for is naive (MySQL DATETIME); treat as UTC for the
                # offset calculation so the value is timezone-stable.
                ff = forecast_for
                if ff.tzinfo is None:
                    ff = ff.replace(tzinfo=timezone.utc)
                offset_hours = max(0, round((ff - now).total_seconds() / 3600))
                forecast_list.append({
                    "offset_hours": offset_hours,
                    "percent": int(score),
                    "level": level,
                    "forecast_for": ff.isoformat(),
                    "estimated_wait_minutes": int(wait_minutes) if wait_minutes is not None else None,
                })

            best = min(forecast_list, key=lambda x: x["percent"])
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
                "data_mode": "forecast",
                "forecast_source": "busyness_forecasts",
            })
    except Exception:
        pass  # fall through to legacy forecast_1h, then mock

    # --- Migration fallback: busyness_scores.forecast_1h JSON ---
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
                        "data_mode": "predicted",
                        "forecast_source": "busyness_scores.forecast_1h",
                    })
        finally:
            conn.close()
    except Exception:
        pass  # fall through to mock

    # --- Final fallback: mock data ---
    forecast = VENUE_FORECASTS.get(venue_id)
    if not forecast:
        return jsonify({"error": "Venue not found."}), 404

    response = deepcopy(forecast)
    response["data_mode"] = "mock"
    response["forecast_source"] = "mock_data"
    return jsonify(response)

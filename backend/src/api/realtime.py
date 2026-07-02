import json
import os
from datetime import datetime, timedelta

import pymysql
from flask import Blueprint, Response

from auth import require_api_key
from mock_data import REALTIME_MAP_UPDATES_EXAMPLE


bp = Blueprint("realtime", __name__)


def _get_db_conn():
    return pymysql.connect(
        host=os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
        user=os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
    )


def _iso_z(value):
    return value.isoformat() + "Z" if value else None


def _live_venue_update_events():
    conn = _get_db_conn()
    try:
        with conn.cursor() as cur:
            since = datetime.now() - timedelta(minutes=5)
            cur.execute(
                "SELECT venue_id, score, level, estimated_wait_minutes, created_at, forecast_end_time "
                "FROM busyness_scores "
                "WHERE model_version = %s AND created_at >= %s "
                "ORDER BY created_at DESC LIMIT 200",
                ("live-telemetry-v1", since),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    events = []
    for venue_id, score, level, wait_minutes, created_at, expires_at in rows:
        payload = {
            "venue_id": venue_id,
            "busyness_score": score,
            "busyness_status": level,
            "estimated_wait_minutes": wait_minutes,
            "updated_at": _iso_z(created_at),
            "expires_at": _iso_z(expires_at),
        }
        events.append(f"event: venue_update\ndata: {json.dumps(payload)}\n\n")
    return events


@bp.get("/api/v1/realtime/map-updates")
@require_api_key
def subscribe_map_updates():
    try:
        events = _live_venue_update_events()
    except Exception:
        events = []

    body = "".join(events or REALTIME_MAP_UPDATES_EXAMPLE)
    return Response(body, mimetype="text/event-stream")

import json
import os
import time
from datetime import datetime, timedelta

import pymysql
from flask import Blueprint, Response, request, stream_with_context

from auth import require_api_key
from mock_data import REALTIME_MAP_UPDATES_EXAMPLE, REPORTS
from sos_buffer import drain_sos_events


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


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def generate_live_stream(poll_interval_seconds: float = 1.0, max_iterations=None):
    """Long-lived SSE generator: on each tick, pushes any buffered SOS
    telemetry and any newly submitted crowdsourced reports, plus a
    heartbeat comment so proxies/clients know the connection is alive.

    `max_iterations` lets tests drive a bounded number of ticks instead of
    looping forever; production callers leave it as None.
    """
    last_report_count = 0
    iterations = 0

    while max_iterations is None or iterations < max_iterations:
        for sos_event in drain_sos_events():
            yield _format_sse("sos_telemetry", sos_event)

        if len(REPORTS) > last_report_count:
            for report in REPORTS[last_report_count:]:
                yield _format_sse("map_update", report)
            last_report_count = len(REPORTS)

        yield ": heartbeat\n\n"

        iterations += 1
        if max_iterations is None:
            time.sleep(poll_interval_seconds)


@bp.get("/api/v1/realtime/stream")
@require_api_key
def stream_live_updates():
    """Persistent SSE channel pushing crowdsourced map updates and SOS
    telemetry to connected map clients as they happen."""
    poll_interval = float(request.args.get("poll_interval_seconds", 1.0))
    return Response(
        stream_with_context(generate_live_stream(poll_interval_seconds=poll_interval)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

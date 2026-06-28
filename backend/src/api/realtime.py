from flask import Blueprint, Response

from auth import require_api_key
from mock_data import REALTIME_MAP_UPDATES_EXAMPLE


bp = Blueprint("realtime", __name__)


@bp.get("/api/v1/realtime/map-updates")
@require_api_key
def subscribe_map_updates():
    body = "".join(REALTIME_MAP_UPDATES_EXAMPLE)
    return Response(body, mimetype="text/event-stream")

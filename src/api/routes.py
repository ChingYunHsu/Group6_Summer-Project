from copy import deepcopy

from flask import Blueprint, jsonify

from auth import require_api_key
from mock_data import ROUTE_DETAIL, ROUTE_OPTIONS


bp = Blueprint("routes", __name__)


@bp.get("/api/v1/routes/options")
@require_api_key
def get_route_options():
    return jsonify(deepcopy(ROUTE_OPTIONS))


@bp.get("/api/v1/routes/detail")
@require_api_key
def get_route_detail():
    return jsonify(deepcopy(ROUTE_DETAIL))

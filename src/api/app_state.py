from copy import deepcopy

from flask import Blueprint, jsonify

from auth import require_api_key
from mock_data import APP_STATE


bp = Blueprint("app_state", __name__)


@bp.get("/api/v1/app-state")
@require_api_key
def get_app_state():
    return jsonify(deepcopy(APP_STATE))

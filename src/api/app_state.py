from copy import deepcopy

from flask import Blueprint, jsonify

from auth import get_current_session, require_api_key
from mock_data import APP_STATE


bp = Blueprint("app_state", __name__)


@bp.get("/api/v1/app-state")
@require_api_key
def get_app_state():
    state = deepcopy(APP_STATE)

    session = get_current_session()
    if session is None:
        state["is_guest"] = True
        state["is_authenticated"] = False
    else:
        state["is_guest"] = session["is_guest"]
        state["is_authenticated"] = not session["is_guest"]

    return jsonify(state)

from copy import deepcopy

from flask import Blueprint, jsonify, request

from auth import require_api_key
from mock_data import CHATBOT_RESPONSE


bp = Blueprint("chatbot", __name__)


@bp.post("/api/v1/chatbot")
@require_api_key
def ask_chatbot():
    payload = request.get_json(silent=True) or {}

    if "message" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["message"]}), 400

    response = deepcopy(CHATBOT_RESPONSE)
    if "language" in payload:
        response["language"] = payload["language"]

    return jsonify(response)

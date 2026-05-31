from flask import Blueprint, current_app, jsonify

from auth import require_api_key


bp = Blueprint("integrations", __name__)


@bp.get("/api/v1/integrations/status")
@require_api_key
def integrations_status():
    return jsonify(
        {
            "besttime": {"configured": bool(current_app.config.get("BESTTIME_API_KEY", ""))},
            "google_maps": {"configured": bool(current_app.config.get("GOOGLE_MAPS_API_KEY", ""))},
            "gemini": {"configured": bool(current_app.config.get("GEMINI_API_KEY", ""))},
        }
    )
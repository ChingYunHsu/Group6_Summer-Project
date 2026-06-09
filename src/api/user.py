from copy import deepcopy

from flask import Blueprint, jsonify

from auth import require_api_key
from mock_data import (
    EMERGENCY_CONTACTS,
    FAVOURITES,
    LANGUAGE_OPTIONS,
    MEDICAL_ID,
    USER_PROFILE,
    USER_SETTINGS,
)


bp = Blueprint("user", __name__)


@bp.get("/api/v1/user/profile")
@require_api_key
def get_user_profile():
    return jsonify(deepcopy(USER_PROFILE))


@bp.get("/api/v1/user/medical-id")
@require_api_key
def get_medical_id():
    return jsonify(deepcopy(MEDICAL_ID))


@bp.get("/api/v1/user/emergency-contacts")
@require_api_key
def get_emergency_contacts():
    return jsonify({"count": len(EMERGENCY_CONTACTS), "items": deepcopy(EMERGENCY_CONTACTS)})


@bp.get("/api/v1/user/settings")
@require_api_key
def get_user_settings():
    return jsonify(deepcopy(USER_SETTINGS))


@bp.get("/api/v1/user/languages")
@require_api_key
def get_language_options():
    return jsonify({"count": len(LANGUAGE_OPTIONS), "items": deepcopy(LANGUAGE_OPTIONS)})


@bp.get("/api/v1/user/favourites")
@require_api_key
def get_favourites():
    return jsonify({"count": len(FAVOURITES), "items": deepcopy(FAVOURITES)})

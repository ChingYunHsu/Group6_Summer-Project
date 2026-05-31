from flask import Blueprint, jsonify


bp = Blueprint("health", __name__)


@bp.get("/api/v1/health")
def health_check():
    return jsonify({"status": "ok", "service": "mock-api", "version": "v1"})
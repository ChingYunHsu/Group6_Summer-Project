from flask import Flask

import db
from api.app_state import bp as app_state_bp
from api.auth import bp as auth_bp
from api.chatbot import bp as chatbot_bp
from api.health import bp as health_bp
from api.integrations import bp as integrations_bp
from api.medical import bp as medical_bp
from api.realtime import bp as realtime_bp
from api.routes import bp as routes_bp
from api.reports import bp as reports_bp
from api.venues import bp as venues_bp
from api.insights import bp as insights_bp
from api.user import bp as user_bp
from settings import get_settings


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(__name__)
    app.config["API_KEY"] = settings.api_key
    app.config["BESTTIME_API_KEY"] = settings.besttime_api_key
    app.config["GOOGLE_MAPS_API_KEY"] = settings.google_maps_api_key
    app.config["GEMINI_API_KEY"] = settings.gemini_api_key
    app.config["JWT_SECRET"] = settings.jwt_secret

    if settings.db_encryption_check_enabled:
        db.verify_tablespace_encryption()

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(app_state_bp)
    app.register_blueprint(venues_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(realtime_bp)

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    app.run(host="0.0.0.0", port=settings.port, debug=settings.flask_env == "development")

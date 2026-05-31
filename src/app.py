from flask import Flask

from api.health import bp as health_bp
from api.integrations import bp as integrations_bp
from api.reports import bp as reports_bp
from api.venues import bp as venues_bp
from settings import get_settings


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(__name__)
    app.config["API_KEY"] = settings.api_key
    app.config["BESTTIME_API_KEY"] = settings.besttime_api_key
    app.config["GOOGLE_MAPS_API_KEY"] = settings.google_maps_api_key
    app.config["GEMINI_API_KEY"] = settings.gemini_api_key

    app.register_blueprint(health_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(venues_bp)
    app.register_blueprint(reports_bp)

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    app.run(host="0.0.0.0", port=settings.port, debug=settings.flask_env == "development")
import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str
    besttime_api_key: str
    google_maps_api_key: str
    gemini_api_key: str
    port: int
    flask_env: str
    # Database
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    # JWT
    jwt_secret_key: str
    jwt_expiration_hours: int


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("API_KEY", ""),
        besttime_api_key=os.getenv("BESTTIME_API_KEY", ""),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        port=int(os.getenv("PORT", "5000")),
        flask_env=os.getenv("FLASK_ENV", "production"),
        # Database
        db_host=os.getenv("CLEARPATH_DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("CLEARPATH_DB_PORT", "3306")),
        db_user=os.getenv("CLEARPATH_DB_USER", "clearpath_app"),
        db_password=os.getenv("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        db_name=os.getenv("CLEARPATH_DB_NAME", "clearpath"),
        # JWT
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "clearpath-dev-secret-change-in-production"),
        jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
    )


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
    jwt_secret: str
    port: int
    flask_env: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout: int
    db_pool_recycle: int
    db_encryption_check_enabled: bool
    redis_url: str


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("API_KEY", ""),
        besttime_api_key=os.getenv("BESTTIME_API_KEY", ""),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        jwt_secret=os.getenv("JWT_SECRET", "dev-insecure-jwt-secret"),
        port=int(os.getenv("PORT", "5000")),
        flask_env=os.getenv("FLASK_ENV", "production"),
        db_host=os.getenv("DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("DB_PORT", "3306")),
        db_user=os.getenv("DB_USER", "clearpath_app"),
        db_password=os.getenv("DB_PASSWORD", "clearpath_app"),
        db_name=os.getenv("DB_NAME", "clearpath"),
        db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        db_pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        db_pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        db_encryption_check_enabled=os.getenv("DB_ENCRYPTION_CHECK", "false").lower() == "true",
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )


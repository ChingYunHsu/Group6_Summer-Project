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


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("API_KEY", ""),
        besttime_api_key=os.getenv("BESTTIME_API_KEY", ""),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        jwt_secret=os.getenv("JWT_SECRET", "dev-insecure-jwt-secret"),
        port=int(os.getenv("PORT", "5000")),
        flask_env=os.getenv("FLASK_ENV", "production"),
    )


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


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("API_KEY", ""),
        besttime_api_key=os.getenv("BESTTIME_API_KEY", ""),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    )
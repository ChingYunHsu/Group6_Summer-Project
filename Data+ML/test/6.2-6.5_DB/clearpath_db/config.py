import os
from pathlib import Path


def discover_project_root(start=None):
    start_path = Path(start or Path.cwd()).resolve()
    candidates = [start_path, *start_path.parents]
    return next(
        (candidate for candidate in candidates if (candidate / "Data+ML").is_dir()),
        start_path,
    )


PROJECT_ROOT = Path(
    os.environ.get("CLEARPATH_PROJECT_ROOT", discover_project_root())
).expanduser().resolve()
DATA_ROOT = Path(
    os.environ.get("CLEARPATH_DATA_ROOT", PROJECT_ROOT.parent / "data_source")
).expanduser().resolve()
MANIFEST_PATH = PROJECT_ROOT / "Data+ML/test/6.2-6.5_DB/clearpath_sources.json"
SCHEMA_PATH = PROJECT_ROOT / "docker/mysql/init/001_clearpath_schema.sql"

MYSQL_CONFIG = {
    "host": os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
    "user": os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
    "password": os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
    "database": os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
    "charset": "utf8mb4",
}

MANHATTAN_BBOX = {
    "lat_min": 40.700,
    "lat_max": 40.880,
    "lng_min": -74.020,
    "lng_max": -73.900,
}
NYC_BBOX = {
    "lat_min": 40.490,
    "lat_max": 40.920,
    "lng_min": -74.260,
    "lng_max": -73.700,
}
COUNTY_BOROUGH = {
    "New York": "Manhattan",
    "Kings": "Brooklyn",
    "Queens": "Queens",
    "Bronx": "Bronx",
    "Richmond": "Staten Island",
}
OSM_CATEGORY_MAP = {
    "hospital": "hospital",
    "clinic": "clinic",
    "doctors": "clinic",
    "pharmacy": "pharmacy",
    "dentist": "dentist",
    "laboratory": "laboratory",
}

import hashlib
from decimal import Decimal

from .config import MANHATTAN_BBOX


# is_manhattan: Check if coordinates fall within Manhattan bounding box
# Params: lat (latitude), lng (longitude)
# Returns: bool, True if coordinates are within MANHATTAN_BBOX
def is_manhattan(lat, lng):
    return (
        MANHATTAN_BBOX["lat_min"] <= float(lat) <= MANHATTAN_BBOX["lat_max"]
        and MANHATTAN_BBOX["lng_min"] <= float(lng) <= MANHATTAN_BBOX["lng_max"]
    )


# gps_to_district: Coarsely map GPS coordinates to Manhattan district
# Split by lat/lng thresholds into uptown / midtown_east / midtown_west / downtown
# Params: lat (latitude), lng (longitude)
# Returns: str, district name
def gps_to_district(lat, lng):
    lat, lng = float(lat), float(lng)
    if lat > 40.800:
        return "uptown"
    if lat > 40.750:
        return "midtown_east" if lng > -73.975 else "midtown_west"
    return "downtown"


# source_hash: Join fields by pipe and take first 36 chars of SHA-256 as dedup fingerprint
# Params: *parts, any number of hashable fields, empty values are skipped
# Returns: str, 36-char hex hash string
def source_hash(*parts):
    payload = "|".join(str(part) for part in parts if part)
    return hashlib.sha256(payload.encode()).hexdigest()[:36]


# gen_vid: Generate unique venue ID from source name and original ID (source_hash wrapper)
# Params: source (data source identifier), source_id (original record ID)
# Returns: str, 36-char hex hash string
def gen_vid(source, source_id):
    return source_hash(source, source_id)


# safe_int: Safely convert to int, returns None on failure
# Params: value (value to convert)
# Returns: int | None
def safe_int(value):
    try:
        return int(float(str(value).strip())) if value and str(value).strip() else None
    except (ValueError, TypeError, OverflowError):
        return None


# safe_dec: Safely convert to Decimal for precise decimal arithmetic
# Params: value (value to convert)
# Returns: Decimal | None
def safe_dec(value):
    try:
        return Decimal(str(value).strip()) if value and str(value).strip() else None
    except (ValueError, TypeError, ArithmeticError):
        return None


# validate_coords: Validate that lat/lng fall within the specified bounding box
# Params: lat (latitude), lng (longitude), bbox (dict with lat_min/lat_max/lng_min/lng_max)
# Returns: bool
def validate_coords(lat, lng, bbox):
    try:
        lat_value, lng_value = float(lat), float(lng)
    except (ValueError, TypeError):
        return False
    return (
        bbox["lat_min"] <= lat_value <= bbox["lat_max"]
        and bbox["lng_min"] <= lng_value <= bbox["lng_max"]
    )


# check_row: Check that all required fields in a data row are present and non-empty
# Params: row (data row dict), required_fields (list of required field names)
# Returns: bool, True if all required fields exist and are non-empty
def check_row(row, required_fields):
    return all(str(row.get(field, "") or "").strip() for field in required_fields)


# fill_missing: Replace None or empty string values with a default
# Params: value (original value), default (replacement value, default None)
# Returns: same type as value or default type
def fill_missing(value, default=None):
    return value if value not in (None, "") else default

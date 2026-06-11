import hashlib
from decimal import Decimal

from .config import MANHATTAN_BBOX


def is_manhattan(lat, lng):
    return (
        MANHATTAN_BBOX["lat_min"] <= float(lat) <= MANHATTAN_BBOX["lat_max"]
        and MANHATTAN_BBOX["lng_min"] <= float(lng) <= MANHATTAN_BBOX["lng_max"]
    )


def gps_to_district(lat, lng):
    lat, lng = float(lat), float(lng)
    if lat > 40.800:
        return "uptown"
    if lat > 40.750:
        return "midtown_east" if lng > -73.975 else "midtown_west"
    return "downtown"


def source_hash(*parts):
    payload = "|".join(str(part) for part in parts if part)
    return hashlib.sha256(payload.encode()).hexdigest()[:36]


def gen_vid(source, source_id):
    return source_hash(source, source_id)


def safe_int(value):
    try:
        return int(float(str(value).strip())) if value and str(value).strip() else None
    except (ValueError, TypeError, OverflowError):
        return None


def safe_dec(value):
    try:
        return Decimal(str(value).strip()) if value and str(value).strip() else None
    except (ValueError, TypeError, ArithmeticError):
        return None


def validate_coords(lat, lng, bbox):
    try:
        lat_value, lng_value = float(lat), float(lng)
    except (ValueError, TypeError):
        return False
    return (
        bbox["lat_min"] <= lat_value <= bbox["lat_max"]
        and bbox["lng_min"] <= lng_value <= bbox["lng_max"]
    )


def check_row(row, required_fields):
    return all(str(row.get(field, "") or "").strip() for field in required_fields)


def fill_missing(value, default=None):
    return value if value not in (None, "") else default

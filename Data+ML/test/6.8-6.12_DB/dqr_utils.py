"""
dqr_utils.py — Shared utilities for ClearPath data quality analysis.

Extracted from database_build.ipynb to avoid code duplication.
Import via: sys.path.insert(0, '<path-to-6.2-6.5_DB>'); from dqr_utils import ...
"""

import os
import hashlib
from math import radians, sin, cos, sqrt, atan2
import pymysql

# ── MySQL ──

MYSQL_CONFIG = {
    'host': os.environ.get('CLEARPATH_DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('CLEARPATH_DB_PORT', '3306')),
    'user': os.environ.get('CLEARPATH_DB_USER', 'clearpath_app'),
    'password': os.environ.get('CLEARPATH_DB_PASSWORD', 'clearpath_app'),
    'database': os.environ.get('CLEARPATH_DB_NAME', 'clearpath'),
    'charset': 'utf8mb4',
}


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


# ── Geospatial ──

MANHATTAN_BOUNDS = {
    'lat_min': 40.700, 'lat_max': 40.882,
    'lng_min': -74.020, 'lng_max': -73.907,
}


def is_manhattan(lat, lng):
    return (MANHATTAN_BOUNDS['lat_min'] <= lat <= MANHATTAN_BOUNDS['lat_max'] and
            MANHATTAN_BOUNDS['lng_min'] <= lng <= MANHATTAN_BOUNDS['lng_max'])


def gps_to_district(lat, lng):
    if lat >= 40.800:
        return 'uptown'
    elif lat >= 40.750:
        return 'midtown_east' if lng >= -73.975 else 'midtown_west'
    else:
        return 'downtown'


def validate_coords(lat, lng, bbox=None):
    if lat is None or lng is None:
        return False, 'Missing coordinates'
    try:
        lat, lng = float(lat), float(lng)
    except (ValueError, TypeError):
        return False, 'Invalid coordinate format'
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False, 'Coordinates out of range'
    if bbox:
        if not (bbox['lat_min'] <= lat <= bbox['lat_max'] and bbox['lng_min'] <= lng <= bbox['lng_max']):
            return False, 'Coordinates outside bbox'
    return True, None


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ── Hashing ──

def source_hash(*parts):
    raw = '|'.join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:36]


def gen_vid(source, sid):
    return source_hash(source, sid)

"""dqr_utils.py — shared utility library.

Contains 3 categories of tools:
  1. Database connection (MySQL)
  2. Geospatial (coordinate validation, district lookup, distance calculation)
  3. External data APIs (traffic, weather)
"""

import os
import hashlib
from math import radians, sin, cos, sqrt, atan2
import pymysql
import pandas as pd

# ── MySQL database connection ──

# MYSQL_CONFIG: read from environment variables, supports Docker and local dev
MYSQL_CONFIG = {
    'host': os.environ.get('CLEARPATH_DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('CLEARPATH_DB_PORT', '3306')),
    'user': os.environ.get('CLEARPATH_DB_USER', 'clearpath_app'),
    'password': os.environ.get('CLEARPATH_DB_PASSWORD', 'clearpath_app'),
    'database': os.environ.get('CLEARPATH_DB_NAME', 'clearpath'),
    'charset': 'utf8mb4',
}


def get_conn():
    """Create a MySQL connection (pymysql). Caller must close() after use."""
    return pymysql.connect(**MYSQL_CONFIG)


# ── Geospatial utilities ──

# MANHATTAN_BOUNDS: lat/lng bounding box for Manhattan (coordinate validation and map clipping)
MANHATTAN_BOUNDS = {
    'lat_min': 40.700, 'lat_max': 40.882,  # latitude range
    'lng_min': -74.020, 'lng_max': -73.907,  # longitude range
}


def is_manhattan(lat, lng):
    """Return True if coordinates fall within Manhattan bounds."""
    return (MANHATTAN_BOUNDS['lat_min'] <= lat <= MANHATTAN_BOUNDS['lat_max'] and
            MANHATTAN_BOUNDS['lng_min'] <= lng <= MANHATTAN_BOUNDS['lng_max'])


def gps_to_district(lat, lng):
    """Map lat/lng to district: uptown / midtown_east / midtown_west / downtown."""
    if lat >= 40.800:
        return 'uptown'
    elif lat >= 40.750:
        return 'midtown_east' if lng >= -73.975 else 'midtown_west'
    else:
        return 'downtown'


def validate_coords(lat, lng, bbox=None):
    """Validate coordinate format and range. Returns (is_valid, error_message)."""
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
    """Compute great-circle distance between two points (meters)."""
    R = 6371000  # Earth radius (meters)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ── Hash utilities ──

def source_hash(*parts):
    """Generate a 36-char truncated SHA256 hash for data provenance and venue_id generation."""
    raw = '|'.join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:36]


def gen_vid(source, sid):
    """Generate a venue_id from source name + source record id."""
    return source_hash(source, sid)


# ═══════════════════════════════════════════════════════════════
# External Data (from external_ingestion.py)
# ═══════════════════════════════════════════════════════════════

import requests as _requests

# SODA_BASE: NYC Traffic Data API (NYC Open Data)
SODA_BASE = 'https://data.cityofnewyork.us/resource/7ym2-wayt.json'
# NWS_HEADERS: Weather API request headers (User-Agent required, otherwise rejected)
NWS_HEADERS = {'User-Agent': 'ClearPath-DQR/1.0 (research-project)'}


def fetch_traffic_hourly(year=2025, boro='Manhattan'):
    """Fetch traffic volume data from NYC SODA API (server-side aggregation to hourly level)."""
    params = {
        '$select': 'segmentid,street,fromst,tost,direction,hh,avg(vol) as avg_vol,count(*) as n_records',
        '$where': f"boro='{boro}' AND yr='{year}'",
        '$group': 'segmentid,street,fromst,tost,direction,hh',
        '$order': 'segmentid,hh',
        '$limit': 50000,
    }
    print(f'Querying SODA API: boro={boro}, yr={year}...')
    resp = _requests.get(SODA_BASE, params=params, timeout=30)
    resp.raise_for_status()  # raise on HTTP error
    raw = resp.json()
    print(f'  → {len(raw)} rows returned')
    return pd.DataFrame(raw)


def classify_busyness(avg_vol, peak_vol):
    """Four-level busyness classification: quiet(<0.3) / moderate(0.3-0.7) / busy(>0.7) / no_data(peak=0)."""
    if peak_vol == 0:
        return 'no_data'
    ratio = avg_vol / peak_vol
    if ratio < 0.3:
        return 'quiet'
    elif ratio < 0.7:
        return 'moderate'
    else:
        return 'busy'


def clean_traffic(traffic_df):
    """Clean traffic data: type conversion + compute peak volume + classify busyness."""
    if traffic_df.empty:
        return traffic_df
    df = traffic_df.copy()
    df['avg_vol'] = pd.to_numeric(df['avg_vol'], errors='coerce')
    df['hh'] = pd.to_numeric(df['hh'], errors='coerce')
    df.dropna(subset=['avg_vol', 'hh'], inplace=True)
    peak = df.groupby('segmentid')['avg_vol'].max()  # peak volume per segment
    df['peak_vol'] = df['segmentid'].map(peak)
    df['busyness_level'] = df.apply(lambda r: classify_busyness(r['avg_vol'], r['peak_vol']), axis=1)
    df['hour'] = df['hh'].astype(int)
    print(f'Traffic cleaned: {len(df)} rows, {df["segmentid"].nunique()} segments')
    return df


def classify_weather_risk(condition):
    """Weather risk classification: high(thunderstorm/snow/...) / medium(rain/wind/...) / low(clear)."""
    high = ['thunderstorm', 'snow', 'blizzard', 'ice', 'tornado']
    medium = ['rain', 'wind', 'fog', 'sleet']
    c = condition.lower()
    if any(k in c for k in high):
        return 'high'
    elif any(k in c for k in medium):
        return 'medium'
    return 'low'


def fetch_weather_nws():
    """Fetch current weather forecast from NWS API (Manhattan grid point)."""
    from datetime import datetime as _dt
    url = 'https://api.weather.gov/gridpoints/OKX/33,37/forecast'  # NYC grid point
    resp = _requests.get(url, headers=NWS_HEADERS, timeout=10)
    resp.raise_for_status()
    current = resp.json()['properties']['periods'][0]  # first period
    return {
        'timestamp': _dt.now().isoformat(),
        'condition': current.get('shortForecast', ''),
        'temperature_c': round((current.get('temperature', 0) - 32) * 5 / 9, 1),  # °F → °C
        'wind_speed_kmh': 0,  # NWS does not provide wind speed; set to 0
    }


def fetch_and_clean_weather(raise_errors=False):
    """Fetch and clean weather data. Returns empty DataFrame on failure (unless raise_errors=True)."""
    try:
        w = fetch_weather_nws()
        w['risk_level'] = classify_weather_risk(w['condition'])  # append risk level
        print(f'Weather: {w["condition"]}, {w["temperature_c"]}C, risk={w["risk_level"]}')
        return pd.DataFrame([w])
    except Exception as e:
        if raise_errors:
            raise
        print(f'Weather fetch failed: {e}')
        return pd.DataFrame()  # 失败时返回空表，不中断流程

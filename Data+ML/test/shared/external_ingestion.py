"""
external_ingestion.py — External data fetching for the DQR pipeline.

Traffic (NYC SODA API) and weather (NWS API).
"""

from datetime import datetime

import pandas as pd
import requests


# ── Constants ─────────────────────────────────────────────────

SODA_BASE = 'https://data.cityofnewyork.us/resource/7ym2-wayt.json'
NWS_HEADERS = {'User-Agent': 'ClearPath-DQR/1.0 (research-project)'}


# ── Traffic ───────────────────────────────────────────────────

def fetch_traffic_hourly(year=2025, boro='Manhattan'):
    """Query Manhattan traffic via SoQL API, server-side aggregation to hourly."""
    params = {
        '$select': 'segmentid,street,fromst,tost,direction,hh,avg(vol) as avg_vol,count(*) as n_records',
        '$where': f"boro='{boro}' AND yr='{year}'",
        '$group': 'segmentid,street,fromst,tost,direction,hh',
        '$order': 'segmentid,hh',
        '$limit': 50000,
    }
    print(f'Querying SODA API: boro={boro}, yr={year}...')
    resp = requests.get(SODA_BASE, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    print(f'  → {len(raw)} rows returned')
    return pd.DataFrame(raw)


def classify_busyness(avg_vol, peak_vol):
    """Four-tier busyness classification per F-06 requirement.

    - quiet:    ratio < 0.3
    - moderate: ratio 0.3–0.7
    - busy:     ratio > 0.7
    - no_data:  peak_vol == 0
    """
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
    """Clean and classify raw traffic data."""
    if traffic_df.empty:
        return traffic_df
    df = traffic_df.copy()
    df['avg_vol'] = pd.to_numeric(df['avg_vol'], errors='coerce')
    df['hh'] = pd.to_numeric(df['hh'], errors='coerce')
    df.dropna(subset=['avg_vol', 'hh'], inplace=True)
    peak = df.groupby('segmentid')['avg_vol'].max()
    df['peak_vol'] = df['segmentid'].map(peak)
    df['busyness_level'] = df.apply(lambda r: classify_busyness(r['avg_vol'], r['peak_vol']), axis=1)
    df['hour'] = df['hh'].astype(int)
    print(f'Traffic cleaned: {len(df)} rows, {df["segmentid"].nunique()} segments')
    print(f'  Busyness distribution: {df["busyness_level"].value_counts().to_dict()}')
    return df


# ── Weather ───────────────────────────────────────────────────

def classify_weather_risk(condition):
    """Classify weather condition into risk level."""
    high = ['thunderstorm', 'snow', 'blizzard', 'ice', 'tornado']
    medium = ['rain', 'wind', 'fog', 'sleet']
    c = condition.lower()
    if any(k in c for k in high):
        return 'high'
    elif any(k in c for k in medium):
        return 'medium'
    return 'low'


def fetch_weather_nws():
    """Fetch current forecast from NWS API."""
    url = 'https://api.weather.gov/gridpoints/OKX/33,37/forecast'
    resp = requests.get(url, headers=NWS_HEADERS, timeout=10)
    resp.raise_for_status()
    current = resp.json()['properties']['periods'][0]
    return {
        'timestamp': datetime.now().isoformat(),
        'condition': current.get('shortForecast', ''),
        'temperature_c': round((current.get('temperature', 0) - 32) * 5 / 9, 1),
        'wind_speed_kmh': 0,
    }


def fetch_and_clean_weather():
    """Fetch weather and return cleaned DataFrame (or empty on failure)."""
    try:
        w = fetch_weather_nws()
        w['risk_level'] = classify_weather_risk(w['condition'])
        print(f'Weather: {w["condition"]}, {w["temperature_c"]}C, risk={w["risk_level"]}')
        return pd.DataFrame([w])
    except Exception as e:
        print(f'Weather fetch failed: {e}')
        return pd.DataFrame()

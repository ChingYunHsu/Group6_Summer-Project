"""busyness_ingestion.py — busyness_scores data ingestion pipeline (venue level).

Data flow:
  NYC SODA Traffic API (with wktgeom) → EPSG:2263→WGS84 conversion
  → aggregate by segment+hour → haversine nearest-venue match (50m)
  → INSERT busyness_scores

Usage:
  cd Data+ML/test/6.8-6.12_DB
  python -m dqr.busyness_ingestion --year 2025 --dry-run
  python -m dqr.busyness_ingestion --year 2025
"""

import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# Support both `python -m dqr.busyness_ingestion` and direct execution
try:
    from dqr_utils import get_conn, gps_to_district
except ImportError:
    import sys
    # The shared DB helpers live in the earlier DB-stage directory.  Keep this
    # historical ingestion script directly runnable rather than depending on a
    # notebook's working directory or a copied helper module.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '6.8-6.12_DB' / 'dqr'))
    from dqr_utils import get_conn, gps_to_district

import requests

# ── Constants ──────────────────────────────────────────────────────

SODA_BASE = 'https://data.cityofnewyork.us/resource/7ym2-wayt.json'
VENUE_MATCH_RADIUS_M = 100  # venue match radius (meters) — 100m covers 68% of segments

# Manhattan bounds
MANHATTAN_BOUNDS = {
    'lat_min': 40.700, 'lat_max': 40.882,
    'lng_min': -74.020, 'lng_max': -73.907,
}


# ── Utility functions ──────────────────────────────────────────

def classify_score(score):
    """Map 0-100 score → four-level category.

    Thresholds based on actual Manhattan traffic distribution (score = avg_vol/peak_vol*100):
    - Manhattan baseline flow is high; scores concentrate in the 55-80 range
    - quiet (<55): off-hours (late night / early morning)
    - moderate (55-70): off-peak hours
    - busy (70-85): peak hours
    - no_data: score=0 or no data
    """
    if score >= 70:
        return 'busy'
    elif score >= 55:
        return 'moderate'
    elif score > 0:
        return 'quiet'
    return 'no_data'


def haversine_m(lat1, lng1, lat2, lng2):
    """Compute haversine distance between two points (meters)."""
    R = 6371000  # Earth radius (meters)
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lng2 - lng1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def parse_wkt_point(wkt):
    """Parse a WKT POINT string → (x, y) coordinates."""
    match = re.match(r'POINT\s*\(([\d.]+)\s+([\d.]+)\)', wkt)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


# Module-level cached Transformer for EPSG:2263 → WGS84
_transformer = None


def epsg2263_to_wgs84(x, y):
    """NYC State Plane (EPSG:2263) → WGS84 (lat/lng). Uses a cached Transformer."""
    global _transformer
    if _transformer is None:
        from pyproj import Transformer
        _transformer = Transformer.from_crs('EPSG:2263', 'EPSG:4326', always_xy=True)
    lng, lat = _transformer.transform(x, y)
    return lat, lng


# ── Step 1: Data collection (with GPS) ────────────────────────────────

def fetch_busyness_data(year=2025, boro='Manhattan'):
    """Fetch traffic data (with wktgeom) from NYC SODA API and convert to WGS84.

    Returns:
        pd.DataFrame: columns segmentid, street, hour, avg_vol, peak_vol,
                      busyness_level, lat, lng
    """
    params = {
        '$select': 'segmentid,street,fromst,tost,direction,hh,'
                   'avg(vol) as avg_vol,count(*) as n_records,wktgeom',
        '$where': f"boro='{boro}' AND yr='{year}'",
        '$group': 'segmentid,street,fromst,tost,direction,hh,wktgeom',
        '$order': 'segmentid,hh',
        '$limit': 50000,
    }
    print(f'Querying SODA API: boro={boro}, yr={year}...')
    resp = requests.get(SODA_BASE, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    print(f'  → {len(raw)} rows returned')

    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)

    # Type conversion
    df['avg_vol'] = pd.to_numeric(df['avg_vol'], errors='coerce')
    df['hh'] = pd.to_numeric(df['hh'], errors='coerce')
    df.dropna(subset=['avg_vol', 'hh'], inplace=True)

    # Parse WKT → WGS84
    coords = df['wktgeom'].apply(parse_wkt_point)
    df['x'] = coords.apply(lambda c: c[0])
    df['y'] = coords.apply(lambda c: c[1])
    # Vectorized batch conversion using cached Transformer
    global _transformer
    if _transformer is None:
        from pyproj import Transformer
        _transformer = Transformer.from_crs('EPSG:2263', 'EPSG:4326', always_xy=True)
    lngs, lats = _transformer.transform(df['x'].values, df['y'].values)
    df['lat'] = lats
    df['lng'] = lngs

    # Filter to Manhattan bounds
    df = df[
        (df['lat'] >= MANHATTAN_BOUNDS['lat_min']) &
        (df['lat'] <= MANHATTAN_BOUNDS['lat_max']) &
        (df['lng'] >= MANHATTAN_BOUNDS['lng_min']) &
        (df['lng'] <= MANHATTAN_BOUNDS['lng_max'])
    ].copy()

    # Compute peak volume and busyness level
    peak = df.groupby('segmentid')['avg_vol'].max()
    df['peak_vol'] = df['segmentid'].map(peak)
    df['busyness_level'] = df.apply(
        lambda r: classify_score(
            int(r['avg_vol'] / r['peak_vol'] * 100) if r['peak_vol'] > 0 else 0
        ), axis=1
    )
    df['hour'] = df['hh'].astype(int)

    # Compute score
    df['score'] = df.apply(
        lambda r: int(r['avg_vol'] / r['peak_vol'] * 100) if r['peak_vol'] > 0 else 0,
        axis=1
    )

    print(f'Traffic cleaned: {len(df)} rows, {df["segmentid"].nunique()} segments '
          f'with GPS')
    return df


# ── Step 2: Segment-level aggregation ───────────────────────────────

def aggregate_by_segment(traffic_df):
    """Aggregate by (segmentid, hour), retaining GPS coordinates.

    Returns:
        pd.DataFrame: columns = [segmentid, street, hour, score, busyness_level, lat, lng]
    """
    if traffic_df.empty:
        return traffic_df

    df = traffic_df.copy()

    # Aggregate by (segmentid, hour), taking average score
    segment_hourly = df.groupby(['segmentid', 'street', 'hour', 'lat', 'lng']).agg(
        avg_vol=('avg_vol', 'mean'),
        peak_vol=('peak_vol', 'max'),
    ).reset_index()

    segment_hourly['score'] = segment_hourly.apply(
        lambda r: int(r['avg_vol'] / r['peak_vol'] * 100) if r['peak_vol'] > 0 else 0,
        axis=1
    )
    segment_hourly['busyness_level'] = segment_hourly['score'].apply(classify_score)

    print(f'Segment aggregation: {len(segment_hourly)} segment-hour rows, '
          f'{df["segmentid"].nunique()} segments')
    return segment_hourly


# ── Step 3: Venue matching (haversine 50m) ───────────────────

def map_segments_to_venues(conn, segment_hourly_df, hours=None):
    """Aggregate traffic segments by district and assign to all venues in the same district.

    The NYC Traffic API only has 28 segments — not enough to cover 1% of the 4,714 venues.
    Instead use district-level aggregation: each segment → gps_to_district() → aggregate by
    (district, hour) → all venues in the same district share that score.

    Returns:
        pd.DataFrame: columns = [venue_id, district, hour, score, busyness_level]
    """
    if segment_hourly_df.empty:
        return pd.DataFrame()

    # 1. Assign a district to each segment
    df = segment_hourly_df.copy()
    df['district'] = df.apply(
        lambda r: gps_to_district(r['lat'], r['lng']), axis=1
    )
    df = df.dropna(subset=['district'])
    n_assigned = df['segmentid'].nunique()
    n_total = segment_hourly_df['segmentid'].nunique()
    print(f'District assignment: {n_assigned}/{n_total} segments mapped '
          f'({n_assigned/n_total*100:.0f}%)')

    # 2. Aggregate by (district, hour), compute weighted-average score
    district_hourly = df.groupby(['district', 'hour']).agg(
        avg_score=('score', 'mean'),
        n_segments=('segmentid', 'nunique'),
    ).reset_index()
    district_hourly['avg_score'] = district_hourly['avg_score'].round(0).astype(int)
    district_hourly['busyness_level'] = district_hourly['avg_score'].apply(classify_score)

    print(f'District aggregation: {len(district_hourly)} district-hour rows, '
          f'{district_hourly["district"].nunique()} districts')

    if hours is not None:
        district_hourly = district_hourly[district_hourly['hour'].isin(hours)].copy()

    # 3. Load all venues and generate one row per venue × hour
    venues_df = pd.read_sql(
        'SELECT venue_id, district FROM venues WHERE district IS NOT NULL',
        conn
    )
    if venues_df.empty:
        print('Warning: no venues with district found')
        return pd.DataFrame()

    # Vectorised district join rather than nested venue×hour iteration. It
    # intentionally retains every hourly profile point for forecast_1h.
    result = venues_df.merge(
        district_hourly[['district', 'hour', 'avg_score', 'busyness_level']],
        on='district', how='inner', validate='many_to_many',
    ).rename(columns={'avg_score': 'score'})
    result['hour'] = result['hour'].astype(int)
    result['score'] = result['score'].astype(int)
    result = result[['venue_id', 'district', 'hour', 'score', 'busyness_level']]
    print(f'Venue mapping: {len(result)} venue-hour rows, '
          f'{venues_df["venue_id"].nunique()} venues across '
          f'{district_hourly["district"].nunique()} districts')
    return result


# ── Step 4: Forecast generation ──────────────────────────────

def build_forecast_1h(scores_df, target_hour):
    """Generate forecast_1h JSON for a single venue (12-hour rolling window).

    Returns:
        list[dict]: [{"offset_hours": 0, "percent": 20, "level": "quiet"}, ...]
    """
    forecast = []
    for offset in range(12):
        h = (target_hour + offset) % 24
        match = scores_df[scores_df['hour'] == h]
        if not match.empty:
            score = int(match.iloc[0]['score'])
            level = match.iloc[0]['busyness_level']
        else:
            score = 0
            level = 'no_data'
        forecast.append({
            'offset_hours': offset,
            'percent': score,
            'level': level,
        })
    return forecast


# ── Step 5: DB write ─────────────────────────────────────────

def insert_busyness_scores(conn, venue_scores_df,
                           model_version='nyc_traffic_baseline_v1',
                           features_snapshot=None,
                           data_year=2025):
    """Bulk-write busyness_scores table: 24 rows per venue (one per hour).

    Uses executemany for batch insert, significantly improving performance.
    Upsert on unique constraint allows safe refresh of hour patterns for same source year.

    Args:
        data_year: source data year, also the index date for the static hour pattern.
            Callers may only use it as ``HOUR(forecast_start_time)``, not as a live window.

    Returns:
        int: number of rows inserted
    """
    if venue_scores_df.empty:
        print('No data to insert')
        return 0

    if features_snapshot is None:
        features_snapshot = f'nyc_traffic_{data_year}_manhattan'

    # Stream bounded batches: a full Manhattan run is ~115k venue-hour rows,
    # each with a 12-point JSON array.  Keeping all of them in one Python list
    # risks terminating the process before any current-context row is written.
    batch_size = 1_000
    inserted = 0
    pattern_date = datetime(data_year, 1, 1)
    sql = """
        INSERT INTO busyness_scores
            (venue_id, score, level, estimated_wait_minutes,
             forecast_1h, forecast_start_time, forecast_end_time,
             model_version, features_snapshot_id)
        VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            score = VALUES(score),
            level = VALUES(level),
            forecast_1h = VALUES(forecast_1h),
            forecast_end_time = VALUES(forecast_end_time),
            features_snapshot_id = VALUES(features_snapshot_id)
    """
    cursor = conn.cursor()
    try:
        batch = []
        for venue_id, group in venue_scores_df.groupby('venue_id'):
            by_hour = group.set_index('hour')[['score', 'busyness_level']].to_dict('index')
            for hour in by_hour:
                values = by_hour.get(int(hour))
                if values is None:
                    continue
                score, level = int(values['score']), values['busyness_level']
                forecast = []
                for offset in range(12):
                    next_values = by_hour.get((int(hour) + offset) % 24)
                    forecast.append({
                        'offset_hours': offset,
                        'percent': int(next_values['score']) if next_values else 0,
                        'level': next_values['busyness_level'] if next_values else 'no_data',
                    })
                base_date = pattern_date.replace(hour=int(hour))
                batch.append((
                    venue_id, score, level, json.dumps(forecast), base_date,
                    base_date + timedelta(hours=1), model_version, features_snapshot,
                ))
                if len(batch) >= batch_size:
                    cursor.executemany(sql, batch)
                    inserted += cursor.rowcount
                    batch.clear()
        if batch:
            cursor.executemany(sql, batch)
            inserted += cursor.rowcount
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f'ERROR: Insert failed: {e}')
        raise
    finally:
        cursor.close()
    print(f'Upserted {inserted} busyness_scores rows (batch)')
    return inserted


def retire_legacy_context_scores(conn):
    """Delete obsolete SODA rows that were incorrectly labelled as live context."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM busyness_scores WHERE model_version=%s",
            ("nyc_traffic_context_v1",),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()


# ── Main entry point ─────────────────────────────────────────

def run_pipeline(year=2025, dry_run=False):
    """Full pipeline: collect → aggregate → venue matching → write."""
    model_version = 'nyc_traffic_baseline_v1'
    print('=== Busyness Ingestion Pipeline (venue-level) ===')
    print(f'Year: {year}, Model: {model_version}, Dry-run: {dry_run}')

    # Step 1: Collect (with GPS)
    print('\n[1/4] Fetching traffic data with GPS...')
    traffic = fetch_busyness_data(year=year)
    if traffic.empty:
        print('ERROR: No traffic data. Aborting.')
        return

    # Step 2: Segment aggregation
    print('\n[2/4] Aggregating by segment...')
    segment_hourly = aggregate_by_segment(traffic)
    if segment_hourly.empty:
        print('ERROR: Aggregation produced no data. Aborting.')
        return

    # Step 3: Venue matching (district level)
    print('\n[3/4] Matching segments to venues (district aggregation)...')
    conn = get_conn()
    try:
        # The old context version is semantically invalid for fixed SODA data.
        # Retire it before doing any new static-pattern work.
        retired = 0 if dry_run else retire_legacy_context_scores(conn)
        # SODA is a fixed historical hour-of-day pattern, so all 24 profile
        # points are retained.  Real-time telemetry is ingested separately.
        venue_scores = map_segments_to_venues(conn, segment_hourly, hours=None)
        if venue_scores.empty:
            print('ERROR: No venue mapping. Aborting.')
            return

        # Step 4: DB write
        if dry_run:
            print('\n[4/4] DRY RUN — skipping DB insert')
            print(f'Would insert {len(venue_scores)} venue-hour rows')
            # Show data distribution per district
            dist_stats = venue_scores.groupby('district')['venue_id'].nunique()
            print(f'\nVenues per district:')
            for d, c in dist_stats.items():
                print(f'  {d}: {c} venues')
            print(f'\nSample data:')
            print(venue_scores.head(12).to_string())
        else:
            print('\n[4/4] Writing to busyness_scores...')
            inserted = insert_busyness_scores(
                conn, venue_scores, model_version, data_year=year)
            print(f'Done: {inserted} baseline rows upserted; {retired} legacy context rows retired')
    finally:
        conn.close()

    print('\n=== Pipeline Complete ===')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Busyness data ingestion pipeline')
    parser.add_argument('--year', type=int, default=2025, help='Data year')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate data without DB insert')
    args = parser.parse_args()
    run_pipeline(year=args.year, dry_run=args.dry_run)

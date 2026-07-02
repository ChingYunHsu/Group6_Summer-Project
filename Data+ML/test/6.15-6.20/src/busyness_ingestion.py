"""busyness_ingestion.py — busyness_scores 数据导入管线 (venue 级别)。

数据流:
  NYC SODA Traffic API (含 wktgeom) → EPSG:2263→WGS84 转换
  → 按 segment+hour 聚合 → haversine 匹配最近 venue (50m)
  → INSERT busyness_scores

用法:
  cd Data+ML/test/6.8-6.12_DB
  python -m dqr.busyness_ingestion --year 2025 --dry-run
  python -m dqr.busyness_ingestion --year 2025 --model-version nyc_traffic_baseline_v1
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
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dqr_utils import get_conn, gps_to_district

import requests

# ── 常量 ──────────────────────────────────────────────────────

SODA_BASE = 'https://data.cityofnewyork.us/resource/7ym2-wayt.json'
VENUE_MATCH_RADIUS_M = 100  # venue 匹配半径 (米) — 100m 覆盖 68% segments

# 曼哈顿边界
MANHATTAN_BOUNDS = {
    'lat_min': 40.700, 'lat_max': 40.882,
    'lng_min': -74.020, 'lng_max': -73.907,
}


# ── 工具函数 ──────────────────────────────────────────────────

def classify_score(score):
    """0-100 分数 → 四档等级。

    阈值基于 Manhattan 交通数据实际分布 (score = avg_vol/peak_vol*100):
    - Manhattan baseline 流量高，score 集中在 55-80 区间
    - quiet (<55): 低谷时段 (凌晨/深夜)
    - moderate (55-70): 平峰时段
    - busy (70-85): 高峰时段
    - no_data: score=0 或无数据
    """
    if score >= 70:
        return 'busy'
    elif score >= 55:
        return 'moderate'
    elif score > 0:
        return 'quiet'
    return 'no_data'


def haversine_m(lat1, lng1, lat2, lng2):
    """计算两点间的 haversine 距离 (米)。"""
    R = 6371000  # 地球半径 (米)
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lng2 - lng1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def parse_wkt_point(wkt):
    """解析 WKT POINT 字符串 → (x, y) 坐标。"""
    match = re.match(r'POINT\s*\(([\d.]+)\s+([\d.]+)\)', wkt)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


# Module-level cached Transformer for EPSG:2263 → WGS84
_transformer = None


def epsg2263_to_wgs84(x, y):
    """NYC State Plane (EPSG:2263) → WGS84 (lat/lng)。使用缓存的 Transformer。"""
    global _transformer
    if _transformer is None:
        from pyproj import Transformer
        _transformer = Transformer.from_crs('EPSG:2263', 'EPSG:4326', always_xy=True)
    lng, lat = _transformer.transform(x, y)
    return lat, lng


# ── Step 1: 数据采集 (含 GPS) ────────────────────────────────

def fetch_busyness_data(year=2025, boro='Manhattan'):
    """从 NYC SODA API 拉取交通数据 (含 wktgeom)，转换为 WGS84。

    Returns:
        pd.DataFrame: 含 segmentid, street, hour, avg_vol, peak_vol,
                      busyness_level, lat, lng 列
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

    # 类型转换
    df['avg_vol'] = pd.to_numeric(df['avg_vol'], errors='coerce')
    df['hh'] = pd.to_numeric(df['hh'], errors='coerce')
    df.dropna(subset=['avg_vol', 'hh'], inplace=True)

    # 解析 WKT → WGS84
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

    # 过滤曼哈顿范围
    df = df[
        (df['lat'] >= MANHATTAN_BOUNDS['lat_min']) &
        (df['lat'] <= MANHATTAN_BOUNDS['lat_max']) &
        (df['lng'] >= MANHATTAN_BOUNDS['lng_min']) &
        (df['lng'] <= MANHATTAN_BOUNDS['lng_max'])
    ].copy()

    # 计算峰值和 busyness level
    peak = df.groupby('segmentid')['avg_vol'].max()
    df['peak_vol'] = df['segmentid'].map(peak)
    df['busyness_level'] = df.apply(
        lambda r: classify_score(
            int(r['avg_vol'] / r['peak_vol'] * 100) if r['peak_vol'] > 0 else 0
        ), axis=1
    )
    df['hour'] = df['hh'].astype(int)

    # 计算 score
    df['score'] = df.apply(
        lambda r: int(r['avg_vol'] / r['peak_vol'] * 100) if r['peak_vol'] > 0 else 0,
        axis=1
    )

    print(f'Traffic cleaned: {len(df)} rows, {df["segmentid"].nunique()} segments '
          f'with GPS')
    return df


# ── Step 2: Segment-level 聚合 ───────────────────────────────

def aggregate_by_segment(traffic_df):
    """按 (segmentid, hour) 聚合，保留 GPS 坐标。

    Returns:
        pd.DataFrame: columns = [segmentid, street, hour, score, busyness_level, lat, lng]
    """
    if traffic_df.empty:
        return traffic_df

    df = traffic_df.copy()

    # 按 (segmentid, hour) 聚合，取平均 score
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


# ── Step 3: Venue 匹配 (haversine 50m) ──────────────────────

def map_segments_to_venues(conn, segment_hourly_df):
    """将 traffic segment 按 district 聚合，分配给同 district 所有 venue。

    NYC Traffic API 只有 28 个 segment，无法覆盖 4,714 venues 的 1%。
    改为 district 级别：每个 segment → gps_to_district() → 按 (district, hour) 聚合
    → 同 district 所有 venue 共享该分数。

    Returns:
        pd.DataFrame: columns = [venue_id, district, hour, score, busyness_level]
    """
    if segment_hourly_df.empty:
        return pd.DataFrame()

    # 1. 为每个 segment 分配 district
    df = segment_hourly_df.copy()
    df['district'] = df.apply(
        lambda r: gps_to_district(r['lat'], r['lng']), axis=1
    )
    df = df.dropna(subset=['district'])
    n_assigned = df['segmentid'].nunique()
    n_total = segment_hourly_df['segmentid'].nunique()
    print(f'District assignment: {n_assigned}/{n_total} segments mapped '
          f'({n_assigned/n_total*100:.0f}%)')

    # 2. 按 (district, hour) 聚合，计算加权平均 score
    district_hourly = df.groupby(['district', 'hour']).agg(
        avg_score=('score', 'mean'),
        n_segments=('segmentid', 'nunique'),
    ).reset_index()
    district_hourly['avg_score'] = district_hourly['avg_score'].round(0).astype(int)
    district_hourly['busyness_level'] = district_hourly['avg_score'].apply(classify_score)

    print(f'District aggregation: {len(district_hourly)} district-hour rows, '
          f'{district_hourly["district"].nunique()} districts')

    # 3. 读取所有 venues，为每个 venue × hour 生成一行
    venues_df = pd.read_sql(
        'SELECT venue_id, district FROM venues WHERE district IS NOT NULL',
        conn
    )
    if venues_df.empty:
        print('Warning: no venues with district found')
        return pd.DataFrame()

    rows = []
    for _, venue in venues_df.iterrows():
        v_district = venue['district']
        d_data = district_hourly[district_hourly['district'] == v_district]
        for _, row in d_data.iterrows():
            rows.append({
                'venue_id': venue['venue_id'],
                'district': v_district,
                'hour': int(row['hour']),
                'score': int(row['avg_score']),
                'busyness_level': row['busyness_level'],
            })

    result = pd.DataFrame(rows)
    print(f'Venue mapping: {len(result)} venue-hour rows, '
          f'{venues_df["venue_id"].nunique()} venues across '
          f'{district_hourly["district"].nunique()} districts')
    return result


# ── Step 4: Forecast 生成 ────────────────────────────────────

def build_forecast_1h(scores_df, target_hour):
    """为单个 venue 生成 forecast_1h JSON (12 小时滚动窗口)。

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


# ── Step 5: DB 写入 ─────────────────────────────────────────

def insert_busyness_scores(conn, venue_scores_df,
                           model_version='nyc_traffic_baseline_v1',
                           features_snapshot=None,
                           data_year=2025):
    """批量写入 busyness_scores 表，每个 venue 写 24 行 (每小时一行)。

    使用 executemany 批量插入，显著提升性能。
    INSERT IGNORE + 唯一约束实现幂等写入。

    Args:
        data_year: 源数据年份，用于构建 features_snapshot 和 forecast 时间戳。

    Returns:
        int: 插入行数
    """
    if venue_scores_df.empty:
        print('No data to insert')
        return 0

    if features_snapshot is None:
        features_snapshot = f'nyc_traffic_{data_year}_manhattan'

    # 构建所有参数
    rows = []
    now = datetime(data_year, 1, 1)
    for venue_id, group in venue_scores_df.groupby('venue_id'):
        for hour in range(24):
            hour_row = group[group['hour'] == hour]
            if hour_row.empty:
                continue

            score = int(hour_row.iloc[0]['score'])
            level = hour_row.iloc[0]['busyness_level']

            # forecast_1h: 从该小时开始的 12 小时滚动窗口
            forecast = []
            for offset in range(12):
                h = (hour + offset) % 24
                h_row = group[group['hour'] == h]
                if not h_row.empty:
                    forecast.append({
                        'offset_hours': offset,
                        'percent': int(h_row.iloc[0]['score']),
                        'level': h_row.iloc[0]['busyness_level'],
                    })
                else:
                    forecast.append({
                        'offset_hours': offset,
                        'percent': 0,
                        'level': 'no_data',
                    })

            base_date = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            rows.append((
                venue_id, score, level,
                json.dumps(forecast),
                base_date, base_date + timedelta(hours=12),
                model_version, features_snapshot,
            ))

    # 批量插入 (幂等: UNIQUE KEY uq_busyness_venue_time)
    sql = """
        INSERT IGNORE INTO busyness_scores
            (venue_id, score, level, estimated_wait_minutes,
             forecast_1h, forecast_start_time, forecast_end_time,
             model_version, features_snapshot_id)
        VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s)
    """
    cursor = conn.cursor()
    try:
        cursor.executemany(sql, rows)
        conn.commit()
        inserted = cursor.rowcount
    except Exception as e:
        conn.rollback()
        print(f'ERROR: Insert failed: {e}')
        raise
    finally:
        cursor.close()
    print(f'Inserted {inserted} busyness_scores rows (batch)')
    return inserted


# ── 主入口 ───────────────────────────────────────────────────

def run_pipeline(year=2025, model_version='nyc_traffic_baseline_v1', dry_run=False):
    """完整管线: 采集 → 聚合 → venue 匹配 → 写入。"""
    print('=== Busyness Ingestion Pipeline (venue-level) ===')
    print(f'Year: {year}, Model: {model_version}, Dry-run: {dry_run}')

    # Step 1: 采集 (含 GPS)
    print('\n[1/4] Fetching traffic data with GPS...')
    traffic = fetch_busyness_data(year=year)
    if traffic.empty:
        print('ERROR: No traffic data. Aborting.')
        return

    # Step 2: Segment 聚合
    print('\n[2/4] Aggregating by segment...')
    segment_hourly = aggregate_by_segment(traffic)
    if segment_hourly.empty:
        print('ERROR: Aggregation produced no data. Aborting.')
        return

    # Step 3: Venue 匹配 (district 级别)
    print('\n[3/4] Matching segments to venues (district aggregation)...')
    conn = get_conn()
    try:
        venue_scores = map_segments_to_venues(conn, segment_hourly)
        if venue_scores.empty:
            print('ERROR: No venue mapping. Aborting.')
            return

        # Step 4: DB 写入
        if dry_run:
            print('\n[4/4] DRY RUN — skipping DB insert')
            print(f'Would insert {len(venue_scores)} venue-hour rows')
            # 展示每个 district 的数据分布
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
            print(f'Done: {inserted} rows inserted')
    finally:
        conn.close()

    print('\n=== Pipeline Complete ===')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Busyness data ingestion pipeline')
    parser.add_argument('--year', type=int, default=2025, help='Data year')
    parser.add_argument('--model-version', default='nyc_traffic_baseline_v1',
                        help='Model version tag')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate data without DB insert')
    args = parser.parse_args()
    run_pipeline(year=args.year, model_version=args.model_version, dry_run=args.dry_run)

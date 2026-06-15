"""dqr_utils.py — 共享工具函数库。

包含 3 大类工具：
  1. 数据库连接（MySQL）
  2. 地理空间（坐标校验、区域判断、距离计算）
  3. 外部数据 API（交通、天气）
"""

import os
import hashlib
from math import radians, sin, cos, sqrt, atan2
import pymysql
import pandas as pd

# ── MySQL 数据库连接 ──

# MYSQL_CONFIG: 从环境变量读取数据库配置，支持 Docker 和本地开发
MYSQL_CONFIG = {
    'host': os.environ.get('CLEARPATH_DB_HOST', '127.0.0.1'),   # 数据库主机
    'port': int(os.environ.get('CLEARPATH_DB_PORT', '3306')),   # 端口
    'user': os.environ.get('CLEARPATH_DB_USER', 'clearpath_app'),  # 用户名
    'password': os.environ.get('CLEARPATH_DB_PASSWORD', 'clearpath_app'),  # 密码
    'database': os.environ.get('CLEARPATH_DB_NAME', 'clearpath'),  # 数据库名
    'charset': 'utf8mb4',  # 字符集（支持 emoji）
}


def get_conn():
    """创建 MySQL 连接对象（pymysql）。使用后需手动 close()。"""
    return pymysql.connect(**MYSQL_CONFIG)


# ── 地理空间工具 ──

# MANHATTAN_BOUNDS: 曼哈顿经纬度边界框（用于坐标校验和地图裁剪）
MANHATTAN_BOUNDS = {
    'lat_min': 40.700, 'lat_max': 40.882,  # 纬度范围
    'lng_min': -74.020, 'lng_max': -73.907,  # 经度范围
}


def is_manhattan(lat, lng):
    """判断坐标是否在曼哈顿范围内。"""
    return (MANHATTAN_BOUNDS['lat_min'] <= lat <= MANHATTAN_BOUNDS['lat_max'] and
            MANHATTAN_BOUNDS['lng_min'] <= lng <= MANHATTAN_BOUNDS['lng_max'])


def gps_to_district(lat, lng):
    """根据经纬度判断所属区域：uptown / midtown_east / midtown_west / downtown。"""
    if lat >= 40.800:
        return 'uptown'
    elif lat >= 40.750:
        return 'midtown_east' if lng >= -73.975 else 'midtown_west'
    else:
        return 'downtown'


def validate_coords(lat, lng, bbox=None):
    """校验坐标格式和范围，返回 (is_valid, error_message)。"""
    if lat is None or lng is None:
        return False, 'Missing coordinates' #不存在
    try:
        lat, lng = float(lat), float(lng)
    except (ValueError, TypeError):
        return False, 'Invalid coordinate format' # 格式错误
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False, 'Coordinates out of range' # 超出范围
    if bbox:
        if not (bbox['lat_min'] <= lat <= bbox['lat_max'] and bbox['lng_min'] <= lng <= bbox['lng_max']):
            return False, 'Coordinates outside bbox' # 超出边界框
    return True, None


def haversine_m(lat1, lng1, lat2, lng2):
    """计算两点间的大圆距离（单位：米）。"""
    R = 6371000  # 地球半径（米）
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    """ 距离计算公式
    a = sin²(Δlat/2) + cos(lat₁) · cos(lat₂) · sin²(Δlng/2)
    distance = 2R · arcsin(√a)"""
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ── 哈希工具 ──

def source_hash(*parts):
    """生成 36 位 SHA256 哈希（截断），用于数据溯源和 venue_id 生成。"""
    raw = '|'.join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:36]


def gen_vid(source, sid):
    """从数据源名 + 源 ID 生成 venue_id。"""
    return source_hash(source, sid)


# ═══════════════════════════════════════════════════════════════
# External Data (from external_ingestion.py)
# ═══════════════════════════════════════════════════════════════

import requests as _requests

# SODA_BASE: NYC 交通数据 API 地址（NYC Open Data）
SODA_BASE = 'https://data.cityofnewyork.us/resource/7ym2-wayt.json'
# NWS_HEADERS: 天气 API 请求头（User-Agent 必填，否则被拒）
NWS_HEADERS = {'User-Agent': 'ClearPath-DQR/1.0 (research-project)'}


def fetch_traffic_hourly(year=2025, boro='Manhattan'):
    """从 NYC SODA API 拉取交通流量数据（服务端聚合到小时级）。"""
    params = {
        '$select': 'segmentid,street,fromst,tost,direction,hh,avg(vol) as avg_vol,count(*) as n_records',
        '$where': f"boro='{boro}' AND yr='{year}'",
        '$group': 'segmentid,street,fromst,tost,direction,hh',
        '$order': 'segmentid,hh',
        '$limit': 50000,
    }
    print(f'Querying SODA API: boro={boro}, yr={year}...')
    resp = _requests.get(SODA_BASE, params=params, timeout=30)
    resp.raise_for_status()  # HTTP 错误时抛异常
    raw = resp.json()
    print(f'  → {len(raw)} rows returned')
    return pd.DataFrame(raw)


def classify_busyness(avg_vol, peak_vol):
    """四档拥挤度分类：quiet(<0.3) / moderate(0.3-0.7) / busy(>0.7) / no_data(峰值=0)。"""
    if peak_vol == 0:
        return 'no_data'
    ratio = avg_vol / peak_vol  # 平均/峰值比
    if ratio < 0.3:
        return 'quiet'
    elif ratio < 0.7:
        return 'moderate'
    else:
        return 'busy'


def clean_traffic(traffic_df):
    """清洗交通数据：类型转换 + 计算峰值 + 分类拥挤度。"""
    if traffic_df.empty:
        return traffic_df
    df = traffic_df.copy()
    df['avg_vol'] = pd.to_numeric(df['avg_vol'], errors='coerce')  # 平均流量
    df['hh'] = pd.to_numeric(df['hh'], errors='coerce')            # 小时
    df.dropna(subset=['avg_vol', 'hh'], inplace=True)
    peak = df.groupby('segmentid')['avg_vol'].max()  # 每段峰值流量
    df['peak_vol'] = df['segmentid'].map(peak)
    df['busyness_level'] = df.apply(lambda r: classify_busyness(r['avg_vol'], r['peak_vol']), axis=1)
    df['hour'] = df['hh'].astype(int)
    print(f'Traffic cleaned: {len(df)} rows, {df["segmentid"].nunique()} segments')
    return df


def classify_weather_risk(condition):
    """天气风险分类：high(thunderstorm/snow/...) / medium(rain/wind/...) / low(晴天)。"""
    high = ['thunderstorm', 'snow', 'blizzard', 'ice', 'tornado']
    medium = ['rain', 'wind', 'fog', 'sleet']
    c = condition.lower()
    if any(k in c for k in high):
        return 'high'
    elif any(k in c for k in medium):
        return 'medium'
    return 'low'


def fetch_weather_nws():
    """从 NWS API 获取当前天气预报（曼哈顿区域）。"""
    from datetime import datetime as _dt
    url = 'https://api.weather.gov/gridpoints/OKX/33,37/forecast'  # 纽约网格点
    resp = _requests.get(url, headers=NWS_HEADERS, timeout=10)
    resp.raise_for_status()
    current = resp.json()['properties']['periods'][0]  # 取第一个时段
    return {
        'timestamp': _dt.now().isoformat(),
        'condition': current.get('shortForecast', ''),           # 天气描述
        'temperature_c': round((current.get('temperature', 0) - 32) * 5 / 9, 1),  # °F → °C
        'wind_speed_kmh': 0,  # NWS 未提供风速，暂设为 0
    }


def fetch_and_clean_weather(raise_errors=False):
    """拉取天气数据并清洗，失败时返回空 DataFrame（或抛异常）。"""
    try:
        w = fetch_weather_nws()
        w['risk_level'] = classify_weather_risk(w['condition'])  # 附加风险等级
        print(f'Weather: {w["condition"]}, {w["temperature_c"]}C, risk={w["risk_level"]}')
        return pd.DataFrame([w])
    except Exception as e:
        if raise_errors:
            raise
        print(f'Weather fetch failed: {e}')
        return pd.DataFrame()  # 失败时返回空表，不中断流程

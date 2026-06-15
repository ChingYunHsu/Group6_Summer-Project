import json
import requests
from .db import etl_execute

# ──── 常量定义 ────
WEATHER_API_BASE = "https://api.weather.gov"  # NWS 公共 API 基础 URL
WEATHER_HEADERS = {
    "User-Agent": "ClearPath/1.0 (clearpath-team6@example.com)",  # API 要求的 User-Agent
    "Accept": "application/geo+json",  # 请求 GeoJSON 格式
}
MANHATTAN_LAT = 40.758   # 曼哈顿中心纬度
MANHATTAN_LNG = -73.985  # 曼哈顿中心经度

# test_weather_api: 测试天气 API 连接
# 功能：依次测试 base、points、forecast、stations、observation 5 个端点
# 返回：{"endpoint_name": {"status": int, "ok": bool, "error": str}}
def test_weather_api():
    results = {}       # 存储所有端点测试结果
    points_data = {}   # 存储 points 端点返回的网格数据
    nearest = None     # 最近气象站 ID

    # 测试 1: base 和 points 端点
    endpoints = [
        ("base", f"{WEATHER_API_BASE}/"),
        ("points", f"{WEATHER_API_BASE}/points/{MANHATTAN_LAT},{MANHATTAN_LNG}"),
    ]
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=WEATHER_HEADERS, timeout=10)
            results[name] = {"status": response.status_code, "ok": response.ok}
            if name == "points" and response.ok:
                points_data = response.json()
        except requests.RequestException as error:
            results[name] = {"status": 0, "ok": False, "error": str(error)}

    # 测试 2: forecast 和 stations 端点（依赖 points 数据）
    properties = points_data.get("properties", {})
    for name, url in (
        ("forecast", properties.get("forecast")),
        ("stations", properties.get("observationStations")),
    ):
        if not url:
            results[name] = {"status": 0, "ok": False, "error": f"No {name} URL"}
            continue
        try:
            response = requests.get(url, headers=WEATHER_HEADERS, timeout=10)
            results[name] = {"status": response.status_code, "ok": response.ok}
            # 获取最近气象站 ID
            if name == "stations" and response.ok:
                stations = response.json().get("features", [])
                nearest = (
                    # stations 是一个列表，取第一个（最近的）站点的 stationIdentifier 作为 nearest
                    stations[0]["properties"]["stationIdentifier"] if stations else None
                )
        except requests.RequestException as error:
            results[name] = {"status": 0, "ok": False, "error": str(error)}

    # 测试 3: observation 端点（当前观测数据）
    if nearest:
        try:
            response = requests.get(
                f"{WEATHER_API_BASE}/stations/{nearest}/observations/latest",
                headers=WEATHER_HEADERS,
                timeout=10,
            )
            results["observation"] = {
                "status": response.status_code,
                "ok": response.ok,
            }
        except requests.RequestException as error:
            results["observation"] = {
                "status": 0,
                "ok": False,
                "error": str(error),
            }
    else:
        results["observation"] = {
            "status": 0,
            "ok": False,
            "error": "No station",
        }
    return results


# fetch_current_weather: 获取当前天气数据
# 功能：从 NWS API 获取指定气象站的最新观测数据
# 输入：station_url（气象站 URL，默认 KNYC = 纽约中央公园）
# 返回：{"temperature_c", "humidity_pct", "wind_speed_kmh", "description"}
def fetch_current_weather(station_url=None):
    station_url = station_url or f"{WEATHER_API_BASE}/stations/KNYC"
    response = requests.get(
        f"{station_url}/observations/latest",
        headers=WEATHER_HEADERS,
        timeout=10,
    )
    response.raise_for_status()  # HTTP 错误时抛出异常
    properties = response.json().get("properties", {})
    return {
        "temperature_c": properties.get("temperature", {}).get("value"),
        "humidity_pct": properties.get("relativeHumidity", {}).get("value"),
        "wind_speed_kmh": properties.get("windSpeed", {}).get("value"),
        "description": properties.get("textDescription", ""),
    }


# classify_weather_risk: 天气风险分级
# 功能：根据温度、风速、天气描述判断风险等级
# 输入：current（天气数据字典）
# 返回："high"（高风险）/ "medium"（中风险）/ "low"（低风险）
# 判断逻辑：
#   high: 温度 > 38°C 或 风速 > 50km/h 或 极端天气描述
#   medium: 温度 > 33°C 或 风速 > 30km/h 或 一般恶劣天气
#   low: 其他情况
def classify_weather_risk(current):
    temperature = current.get("temperature_c")
    wind = current.get("wind_speed_kmh")
    description = (current.get("description") or "").lower()

    # 高风险条件
    if temperature and temperature > 38:
        return "high"
    if wind and wind > 50:
        return "high"
    if any(
        word in description
        for word in ("heavy", "thunderstorm", "blizzard", "ice", "snow", "freezing")
    ):
        return "high"

    # 中风险条件
    if temperature and temperature > 33:
        return "medium"
    if wind and wind > 30:
        return "medium"
    if any(
        word in description
        for word in ("rain", "showers", "drizzle", "fog", "mist", "windy")
    ):
        return "medium"

    # 低风险
    return "low"


# etl_weather: 天气 ETL 导入函数
# 功能：获取当前天气并存入 external_context_cache 表
# 输入：conn（数据库连接）
# 缓存策略：
#   - context_type: "weather_current"
#   - request_key: "weather:manhattan"
#   - TTL: 1 小时（expires_at = NOW() + 1 HOUR）
# 返回：{"imported": 1/0, "skipped": 0/1, "errors": 0/1}
def etl_weather(conn):
    try:
        current = fetch_current_weather()
    except requests.RequestException:
        return {"imported": 0, "skipped": 1, "errors": 1}

    # 构建载荷：天气数据 + 风险等级
    payload = {**current, "risk_level": classify_weather_risk(current)}

    # SQL: INSERT ON DUPLICATE KEY UPDATE（幂等操作）
    statement = (
        "INSERT INTO external_context_cache "
        "(context_type, request_key, payload_json, valid_from, expires_at) "
        "VALUES (%s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 1 HOUR)) "
        "ON DUPLICATE KEY UPDATE payload_json = VALUES(payload_json), "
        "valid_from = NOW(), expires_at = DATE_ADD(NOW(), INTERVAL 1 HOUR)",
        (
            "weather_current",           # 缓存类型
            "weather:manhattan",         # 请求键（曼哈顿天气）
            json.dumps(payload, default=str),  # JSON 载荷
        ),
    )

    success = etl_execute(
        conn, statement, source="weather", record_id="weather:manhattan"
    )
    return {
        "imported": int(success),
        "skipped": int(not success),
        "errors": int(not success),
    }

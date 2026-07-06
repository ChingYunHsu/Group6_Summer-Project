"""Build ML feature outputs for the healthcare busyness notebook.

The notebook should stay presentation-focused. This module owns reusable data
loading, feature construction, audit output, and small summary tables.

管线流程:
  1. read_labels()          — 读取 venue_label_status_coverage_view.csv
  2. build_coverage_summary() — 标签状态分布 + healthcare 覆盖率摘要
  3. build_feature_registry() — 特征元数据注册表
  4. build_popular_times()  — 从缓存 JSON 提取逐小时 busyness_score 标签
  5. build_place_features() — 按 serpapi_place_id 分组的 Place 级特征
  6. build_spatial_features() — 地铁/Citi Bike 最近距离 + DB ramp POI 密度
  7. build_capacity_features() — NYS 床位容量 + CMS 医院评级匹配
  8. build_training_frame() — 合并所有特征为最终训练表
  9. build_seasonal_baseline() — 按 (district, day, hour) 的季节性基线
  10. 输出 CSV + manifest

输出目录: Data+ML/test/6.28-7.3/output/
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_modeling import (
    build_ablation_summary,
    build_low_coverage_drop_one_ablation,
    build_low_coverage_imputation_diagnostics,
    build_model_feature_blocks,
    derive_busy_level,
    evaluate_model_family,
)


# ── 常量 ─────────────────────────────────────────────────────────────────────

# NYC 经纬度边界框，用于过滤非 NYC 数据点
NYC_BBOX = {
    "min_lon": -74.35,
    "max_lon": -73.55,
    "min_lat": 40.45,
    "max_lat": 41.05,
}

# 星期名 → 数字索引映射
DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

BUSY_LEVEL_LABELS = ("quiet", "moderate", "busy")


# ── 路径配置 ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelinePaths:
    """管线所有输入/输出路径的不可变容器。"""
    project_root: Path          # 项目根目录 (Group6_Summer-Project)
    output_622: Path            # 6.22-6.27 阶段输出目录
    raw_json_dir: Path          # SerpAPI 缓存 JSON 目录
    label_view: Path            # venue_label_status_coverage_view.csv
    data_source_dir: Path       # 外部数据源目录 (MTA/Citi Bike/NYS/CMS)
    notebook_output_dir: Path   # 本管线输出目录 (6.28-7.3/output)


def find_project_root(start: Path | None = None) -> Path:
    """从当前目录向上查找项目根目录（包含 Data+ML 和 docs 的目录）。"""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "Data+ML").exists() and (candidate / "docs").exists():
            return candidate
    raise FileNotFoundError("Could not find Group6_Summer-Project root from current directory.")


def default_paths(project_root: Path | None = None) -> PipelinePaths:
    """返回默认的 PipelinePaths 实例，包含所有输入/输出路径。"""
    root = find_project_root(project_root)
    data_source_dir = root / "data_source"
    if not data_source_dir.exists():
        data_source_dir = root.parent / "data_source"
    output_622 = root / "Data+ML/test/6.22-6.27/output"
    return PipelinePaths(
        project_root=root,
        output_622=output_622,
        raw_json_dir=output_622 / "serpapi_raw_responses",
        label_view=output_622 / "venue_label_status_coverage_view.csv",
        data_source_dir=data_source_dir,
        notebook_output_dir=root / "Data+ML/test/6.28-7.3/output",
    )


def haversine_distance_m(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371000 * 2 * np.arcsin(np.sqrt(a))


def filter_nyc_points(frame: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> pd.DataFrame:
    """过滤 DataFrame，只保留 NYC 边界框内的点。用于 loader 函数清洗数据。"""
    if frame.empty:
        return frame.copy()
    return frame[
        frame[lat_col].between(NYC_BBOX["min_lat"], NYC_BBOX["max_lat"])
        & frame[lon_col].between(NYC_BBOX["min_lon"], NYC_BBOX["max_lon"])
    ].copy()


def nearest_distance_to_points(venues: pd.DataFrame, points: pd.DataFrame) -> pd.Series:
    """计算每个 venue 到 points 中最近点的距离（米）。用于 nearest_subway/citibike_distance_m 特征。"""
    valid_points = points[["latitude", "longitude"]].dropna().to_numpy(dtype=float)
    if len(valid_points) == 0:
        return pd.Series(np.nan, index=venues.index)

    distances: list[float] = []
    for _, row in venues.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            distances.append(np.nan)
            continue
        d = haversine_distance_m(
            float(row["latitude"]),
            float(row["longitude"]),
            valid_points[:, 0],
            valid_points[:, 1],
        )
        distances.append(float(np.min(d)) if len(d) else np.nan)
    return pd.Series(distances, index=venues.index)


def count_points_within_radius(venues: pd.DataFrame, points: pd.DataFrame, radius_m: float = 300) -> pd.Series:
    """统计每个 venue 半径 radius_m 内的 points 数量。用于 poi_density_300m 特征。"""
    valid_points = points[["latitude", "longitude"]].dropna().to_numpy(dtype=float)
    if len(valid_points) == 0:
        return pd.Series(0, index=venues.index, dtype="int64")

    counts: list[int] = []
    for _, row in venues.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            counts.append(0)
            continue
        d = haversine_distance_m(
            float(row["latitude"]),
            float(row["longitude"]),
            valid_points[:, 0],
            valid_points[:, 1],
        )
        counts.append(int((d <= radius_m).sum()))
    return pd.Series(counts, index=venues.index, dtype="int64")


def parse_hour_label(value: object) -> int | None:
    """将 Google Popular Times 时间标签（如 '8 AM'）转为 24 小时制整数。解析失败返回 None。"""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d{1,2})\s*([AP]M)\s*", value.upper())
    if not match:
        return None
    hour = int(match.group(1))
    if hour == 12:
        hour = 0
    if match.group(2) == "PM":
        hour += 12
    return hour


def parse_clock_time(value: object, fallback_period: str | None = None) -> float | None:
    """将时钟时间字符串（如 '8:30 AM'）转为浮点小时数（如 8.5）。支持 fallback AM/PM 推断。"""
    if not isinstance(value, str):
        return None
    text = value.strip().upper().replace(".", "")
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AP]M)?", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    period = match.group(3) or fallback_period
    if period not in {"AM", "PM"}:
        return None
    if hour == 12:
        hour = 0
    if period == "PM":
        hour += 12
    return hour + minute / 60


def parse_hours_interval(interval_text: str) -> tuple[float, float] | None:
    """解析营业时间区间（如 '8:30 AM–6:30 PM'）为 (start, end) 浮点小时元组。"""
    normalized = (
        interval_text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace(" to ", "-")
    )
    if "-" not in normalized:
        return None
    start_text, end_text = [part.strip() for part in normalized.split("-", 1)]
    end_period_match = re.search(r"([AP]M)\b", end_text.upper())
    fallback_period = end_period_match.group(1) if end_period_match else None
    start = parse_clock_time(start_text, fallback_period=fallback_period)
    end = parse_clock_time(end_text)
    if start is None or end is None:
        return None
    return start, end


def parse_daily_hours(hours_text: object) -> dict[str, Any]:
    """解析 SerpAPI 的单日营业时间字符串，返回 {status, intervals}。支持 24h/closed/区间。"""
    """Parse a SerpAPI day-hours string such as '8:30 AM–6:30 PM'."""
    if not isinstance(hours_text, str) or not hours_text.strip():
        return {"status": "unknown", "intervals": []}
    text = hours_text.strip()
    lowered = text.lower()
    if "open 24 hours" in lowered or lowered == "24 hours":
        return {"status": "open_24h", "intervals": [(0.0, 24.0)]}
    if lowered in {"closed", "temporarily closed"}:
        return {"status": "closed", "intervals": []}

    intervals: list[tuple[float, float]] = []
    for part in re.split(r",|;", text):
        interval = parse_hours_interval(part)
        if interval is not None:
            intervals.append(interval)
    if not intervals:
        return {"status": "unknown", "intervals": []}

    return {"status": "parsed", "intervals": intervals}


def is_hour_in_intervals(hour: int | float | None, intervals: list[tuple[float, float]]) -> bool | Any:
    """判断给定小时是否在营业时间区间内。用于 is_business_hours 特征。"""
    if hour is None or pd.isna(hour):
        return pd.NA
    hour_value = float(hour)
    for start, end in intervals:
        if start <= end:
            if start <= hour_value < end:
                return True
        elif hour_value >= start or hour_value < end:
            return True
    return False


def build_hours_lookup(place: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """从 SerpAPI place_results 构建每天的营业时间查找表。"""
    raw_hours = place.get("hours")
    if not isinstance(raw_hours, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for item in raw_hours:
        
        if not isinstance(item, dict):
            continue
        for day, hours_text in item.items():
            lookup[str(day).lower()] = parse_daily_hours(hours_text)
    return lookup


def normalize_name(value: object) -> str:
    """标准化名称：小写、去标点、去公司后缀（inc/llc/corp 等）。用于名称匹配。"""
    if pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\b(inc|llc|pllc|corp|corporation|company|co|the)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def name_similarity(left: object, right: object) -> float:
    """计算两个名称的 SequenceMatcher 相似度（0–1）。用于 NYS/CMS 设施匹配。"""
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    return float(SequenceMatcher(None, left_norm, right_norm).ratio())


def read_labels(paths: PipelinePaths) -> pd.DataFrame:
    return pd.read_csv(paths.label_view)


def build_coverage_summary(labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """返回两个表：(1) 按 venue_type×label_status 的交叉统计；(2) healthcare 覆盖率摘要（trainable_pct 等）。"""
    status = (
        labels.groupby(["venue_type", "label_status"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    healthcare = labels[labels["venue_type"].eq("healthcare")].copy()
    summary = pd.DataFrame(
        [
            {
                "healthcare_total": len(healthcare),
                "serpapi_matched": int(healthcare["label_status"].isin(["has_popular_times", "no_popular_times"]).sum()),
                "has_popular_times": int(healthcare["label_status"].eq("has_popular_times").sum()),
                "no_popular_times": int(healthcare["label_status"].eq("no_popular_times").sum()),
                "search_not_matched": int(healthcare["label_status"].eq("search_not_matched").sum()),
                "trainable_pct": round(float(healthcare["label_status"].eq("has_popular_times").mean() * 100), 1),
            }
        ]
    )
    return status, summary

# 新增特征
def build_feature_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"feature": "day_of_week", "group": "Temporal", "priority": "P0", "release_stage": "V1", "status": "implemented_popular_times"},
            {"feature": "hour", "group": "Temporal", "priority": "P0", "release_stage": "V1", "status": "implemented_popular_times"},
            {"feature": "is_weekend", "group": "Temporal", "priority": "P0", "release_stage": "V1", "status": "implemented_derived_from_day"},
            {"feature": "review_count", "group": "SerpAPI label", "priority": "P0", "release_stage": "V1", "status": "available_or_nullable"},
            {"feature": "district", "group": "DB direct", "priority": "P0", "release_stage": "V1", "status": "implemented_db_venues"},
            {"feature": "rating", "group": "DB direct", "priority": "P0", "release_stage": "V1", "status": "implemented_db_venues_backfilled_from_serpapi"},
            {"feature": "healthcare_subtype", "group": "DB direct", "priority": "P0", "release_stage": "V1", "status": "implemented_db_healthcare_profiles"},
            {"feature": "opening_hours", "group": "DB direct", "priority": "P1", "release_stage": "V1", "status": "implemented_db_venues"},
            {"feature": "facility_type", "group": "DB direct", "priority": "P1", "release_stage": "V1", "status": "implemented_db_healthcare_profiles"},
            {"feature": "traffic_score", "group": "SerpAPI", "priority": "P0", "release_stage": "V1", "status": "target_proxy_from_popular_times"},
            {"feature": "nearest_subway_distance_m", "group": "Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_local_mta_csv"},
            {"feature": "nearest_citibike_distance_m", "group": "Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_local_gbfs_snapshot"},
            {"feature": "poi_density_300m", "group": "Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_db_pedestrian_ramps"},
            {"feature": "capacity", "group": "NYS/CMS", "priority": "P2", "release_stage": "V1", "status": "implemented_nys_capacity_snapshot"},
            {"feature": "hospital_level", "group": "NYS/CMS", "priority": "P2", "release_stage": "V1", "status": "implemented_nys_facility_match"},
            {"feature": "is_business_hours", "group": "Derived", "priority": "P0", "release_stage": "V1", "status": "implemented_from_serpapi_hours"},
            {"feature": "mapped_venue_count", "group": "SerpAPI", "priority": "P2", "release_stage": "V1", "status": "implemented_from_place_mapping"},
            {"feature": "citibike_nearest_distance_m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "mta_nearest_distance_m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "traffic_nearest_distance_m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "citibike_covered_200m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "mta_covered_200m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "traffic_covered_500m", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_coverage_detail_csv"},
            {"feature": "urban_activity_spatial_score", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_composite_v1"},
            {"feature": "citibike_distance_bin", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_binned_v1"},
            {"feature": "mta_distance_bin", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_binned_v1"},
            {"feature": "traffic_distance_bin", "group": "UrbanActivity_Spatial", "priority": "P1", "release_stage": "V1", "status": "implemented_binned_v1"},
            {"feature": "month", "group": "Temporal", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "is_holiday_or_event", "group": "Temporal", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "mta_hourly_ridership", "group": "UrbanActivity_Hourly", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "citibike_station_activity", "group": "UrbanActivity_Hourly", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "nyc_traffic_hourly_volume", "group": "UrbanActivity_Hourly", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "urban_activity_proxy_score", "group": "UrbanActivity_Hourly", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "weather_condition", "group": "Weather", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "precipitation_mm", "group": "Weather", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "temperature_c", "group": "Weather", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "heat_alert", "group": "Weather", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "transit_disruption_count", "group": "TransitRealtime", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "recent_user_report_count", "group": "CrowdReports", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
            {"feature": "live_capacity_or_wait_time", "group": "LiveCapacity", "priority": "P2", "release_stage": "V2", "status": "v2_not_implemented"},
        ]
    )


def iter_popular_times_rows(raw_json_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_json_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        place = data.get("place_results") or {}
        graph = (place.get("popular_times") or {}).get("graph_results")
        if not isinstance(graph, dict):
            continue
        place_id = place.get("place_id") or (data.get("search_parameters") or {}).get("place_id")
        hours_lookup = build_hours_lookup(place)
        for day, points in graph.items():
            if not isinstance(points, list):
                continue
            day_key = str(day).lower()
            hours_info = hours_lookup.get(day_key, {"status": "unknown", "intervals": []})
            intervals = hours_info["intervals"]
            for point in points:
                if not isinstance(point, dict) or "busyness_score" not in point:
                    continue
                hour = parse_hour_label(point.get("time"))
                rows.append(
                    {
                        "source_file": path.name,
                        "prediction_group_id": place_id,
                        "place_title": place.get("title"),
                        "day_of_week": day_key,
                        "day_index": DAY_INDEX.get(day_key),
                        "hour": hour,
                        "busyness_score": point.get("busyness_score"),
                        "info": point.get("info"),
                        "is_business_hours": is_hour_in_intervals(hour, intervals) if hours_info["status"] != "unknown" else pd.NA,
                        "hours_status": hours_info["status"],
                        "target_type": "google_popular_times_proxy",
                    }
                )
    return rows


def build_popular_times(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """调用 iter_popular_times_rows()，返回 (hourly_df, summary_df)。"""
    rows = pd.DataFrame(iter_popular_times_rows(paths.raw_json_dir))
    summary = pd.DataFrame(
        [
            {
                "json_files_with_rows": rows["source_file"].nunique() if len(rows) else 0,
                "hourly_rows": len(rows),
                "unique_prediction_groups": rows["prediction_group_id"].nunique() if len(rows) else 0,
                "min_hour": rows["hour"].min() if len(rows) else math.nan,
                "max_hour": rows["hour"].max() if len(rows) else math.nan,
                "busyness_min": rows["busyness_score"].min() if len(rows) else math.nan,
                "busyness_max": rows["busyness_score"].max() if len(rows) else math.nan,
            }
        ]
    )
    return rows, summary


def build_place_features(labels: pd.DataFrame) -> pd.DataFrame:
    return (
        labels[labels["serpapi_place_id"].notna()]
        .groupby("serpapi_place_id")
        .agg(
            mapped_venue_count=("venue_id", "nunique"),
            mean_review_count=("review_count", "mean"),
            mean_rating=("rating", "mean"),
        )
        .reset_index()
        .rename(columns={"serpapi_place_id": "prediction_group_id"})
    )


def load_mta_subway_stations(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = paths.data_source_dir / "MTA_Subway_Stations_20260526.csv"
    if not path.exists():
        return pd.DataFrame(columns=["station_id", "station_name", "latitude", "longitude"]), pd.DataFrame(
            [{"source": "MTA Subway Stations", "status": "missing_file", "path": str(path), "rows": 0}]
        )
    raw = pd.read_csv(path)
    stations = raw.rename(
        columns={
            "GTFS Stop ID": "station_id",
            "Stop Name": "station_name",
            "GTFS Latitude": "latitude",
            "GTFS Longitude": "longitude",
        }
    )[["station_id", "station_name", "latitude", "longitude"]].dropna(subset=["latitude", "longitude"])
    stations = filter_nyc_points(stations)
    return stations, pd.DataFrame([{"source": "MTA Subway Stations", "status": "ok", "path": str(path), "rows": len(stations)}])


def load_citibike_stations(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载 Citi Bike GBFS JSON → station_id, station_name, latitude, longitude。"""
    path = paths.data_source_dir / "citibike_station_information.json"
    if not path.exists():
        return pd.DataFrame(columns=["station_id", "station_name", "latitude", "longitude"]), pd.DataFrame(
            [{"source": "Citi Bike GBFS station_information", "status": "missing_file", "path": str(path), "rows": 0}]
        )
    data = json.loads(path.read_text())
    stations = pd.DataFrame(data.get("data", {}).get("stations", []))
    if not {"station_id", "name", "lat", "lon"}.issubset(stations.columns):
        return pd.DataFrame(columns=["station_id", "station_name", "latitude", "longitude"]), pd.DataFrame(
            [{"source": "Citi Bike GBFS station_information", "status": "bad_schema", "path": str(path), "rows": 0}]
        )
    stations = stations.rename(columns={"name": "station_name", "lat": "latitude", "lon": "longitude"})[
        ["station_id", "station_name", "latitude", "longitude"]
    ].dropna(subset=["latitude", "longitude"])
    stations = filter_nyc_points(stations)
    return stations, pd.DataFrame(
        [{"source": "Citi Bike GBFS station_information", "status": "ok", "path": str(path), "rows": len(stations)}]
    )


def db_connection(paths: PipelinePaths):
    import sys

    db_root = paths.project_root / "Data+ML/test/6.2-6.5_DB"
    if str(db_root) not in sys.path:
        sys.path.insert(0, str(db_root))
    from clearpath_db.db import get_conn

    return get_conn()


def read_db_frame(paths: PipelinePaths, query: str) -> pd.DataFrame:
    conn = db_connection(paths)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def load_db_healthcare_features(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    query = """
        SELECT
            v.venue_id,
            v.name,
            v.latitude,
            v.longitude,
            v.district,
            v.opening_hours,
            v.rating,
            v.accessible_status,
            v.accessibility_features,
            p.healthcare_category AS healthcare_subtype,
            p.facility_type
        FROM venues v
        JOIN healthcare_profiles p ON p.venue_id = v.venue_id
        WHERE v.latitude IS NOT NULL AND v.longitude IS NOT NULL
    """
    frame = read_db_frame(paths, query)
    frame = filter_nyc_points(frame)
    return frame, pd.DataFrame(
        [{"source": "db.healthcare_profiles + venues", "status": "ok", "path": "mysql://clearpath", "rows": len(frame)}]
    )


def load_db_accessibility_points(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    query = """
        SELECT ramp_id AS poi_id, latitude, longitude
        FROM pedestrian_ramps
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    frame = read_db_frame(paths, query)
    frame = filter_nyc_points(frame)
    return frame, pd.DataFrame(
        [{"source": "db.pedestrian_ramps", "status": "ok", "path": "mysql://clearpath", "rows": len(frame)}]
    )


def load_db_feature_source_audit(paths: PipelinePaths) -> pd.DataFrame:
    query = """
        SELECT source_name, matched_method, COUNT(*) AS `rows`, ROUND(AVG(match_confidence), 3) AS avg_match_confidence
        FROM venue_source_links
        GROUP BY source_name, matched_method
        ORDER BY source_name, matched_method
    """
    try:
        source_links = read_db_frame(paths, query)
        tables = read_db_frame(
            paths,
            """
            SELECT 'venues' AS source, COUNT(*) AS `rows` FROM venues
            UNION ALL SELECT 'healthcare_profiles' AS source, COUNT(*) AS `rows` FROM healthcare_profiles
            UNION ALL SELECT 'pedestrian_ramps' AS source, COUNT(*) AS `rows` FROM pedestrian_ramps
            UNION ALL SELECT 'venue_source_links' AS source, COUNT(*) AS `rows` FROM venue_source_links
            """,
        )
    except Exception as exc:
        cached = paths.notebook_output_dir / "db_feature_source_audit.csv"
        if cached.exists():
            audit = pd.read_csv(cached)
            audit["status"] = "cached_db_unavailable"
            audit["error"] = f"{type(exc).__name__}: {exc}"
            return audit
        return pd.DataFrame(
            [
                {
                    "source": "mysql://clearpath",
                    "matched_method": pd.NA,
                    "rows": 0,
                    "avg_match_confidence": pd.NA,
                    "status": "db_unavailable",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            ]
        )
    tables["matched_method"] = pd.NA
    tables["avg_match_confidence"] = pd.NA
    tables = tables[["source", "matched_method", "rows", "avg_match_confidence"]]
    source_links = source_links.rename(columns={"source_name": "source"})
    source_links["source"] = source_links["source"].astype(str)
    source_links = source_links[["source", "matched_method", "rows", "avg_match_confidence"]]
    return pd.concat([tables, source_links], ignore_index=True)


def build_spatial_features(paths: PipelinePaths, healthcare: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    subway, subway_audit = load_mta_subway_stations(paths)
    citibike, citibike_audit = load_citibike_stations(paths)
    try:
        db_healthcare, db_healthcare_audit = load_db_healthcare_features(paths)
        pedestrian_ramps, accessibility_audit = load_db_accessibility_points(paths)
    except Exception as exc:
        cached = paths.notebook_output_dir / "spatial_features_v1.csv"
        if cached.exists():
            cached_features = pd.read_csv(cached)
            audit = pd.concat([subway_audit, citibike_audit], ignore_index=True)
            audit = pd.concat(
                [
                    audit,
                    pd.DataFrame(
                        [
                            {
                                "source": "db.healthcare_profiles + pedestrian_ramps",
                                "status": "cached_db_unavailable",
                                "path": str(cached),
                                "rows": len(cached_features),
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
            audit["venues_total"] = len(cached_features)
            audit["venues_missing_coordinates"] = int(cached_features[["latitude", "longitude"]].isna().any(axis=1).sum())
            return cached_features, audit

        db_healthcare = healthcare[
            ["venue_id", "name", "latitude", "longitude", "district", "rating"]
        ].copy()
        db_healthcare["opening_hours"] = pd.NA
        db_healthcare["healthcare_subtype"] = pd.NA
        db_healthcare["facility_type"] = pd.NA
        db_healthcare["accessible_status"] = pd.NA
        db_healthcare_audit = pd.DataFrame(
            [
                {
                    "source": "db.healthcare_profiles + venues",
                    "status": "db_unavailable_label_fallback",
                    "path": "mysql://clearpath",
                    "rows": len(db_healthcare),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            ]
        )
        pedestrian_ramps = pd.DataFrame(columns=["poi_id", "latitude", "longitude"])
        accessibility_audit = pd.DataFrame(
            [
                {
                    "source": "db.pedestrian_ramps",
                    "status": "db_unavailable_empty_fallback",
                    "path": "mysql://clearpath",
                    "rows": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            ]
        )
    out = db_healthcare[
        [
            "venue_id",
            "name",
            "latitude",
            "longitude",
            "district",
            "opening_hours",
            "rating",
            "healthcare_subtype",
            "facility_type",
            "accessible_status",
        ]
    ].copy()
    out["nearest_subway_distance_m"] = nearest_distance_to_points(out, subway).round(1)
    out["nearest_citibike_distance_m"] = nearest_distance_to_points(out, citibike).round(1)
    poi_points = pd.concat(
        [
            db_healthcare[["latitude", "longitude"]],
            pedestrian_ramps[["latitude", "longitude"]],
        ],
        ignore_index=True,
    )
    out["poi_density_300m"] = count_points_within_radius(out, poi_points, radius_m=300)
    out["spatial_features_status"] = np.where(
        out[["nearest_subway_distance_m", "nearest_citibike_distance_m"]].notna().all(axis=1),
        "ok",
        "partial_or_missing_source",
    )
    audit = pd.concat([subway_audit, citibike_audit, db_healthcare_audit, accessibility_audit], ignore_index=True)
    audit["venues_total"] = len(db_healthcare)
    audit["venues_missing_coordinates"] = int(db_healthcare[["latitude", "longitude"]].isna().any(axis=1).sum())
    return out, audit


def load_venue_coverage_features(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """从 6.15-6.20 venue_coverage_detail.csv 读取 Citi Bike / MTA / Traffic 空间覆盖特征。"""
    coverage_path = paths.project_root / "Data+ML/test/6.15-6.20/output/venue_coverage_detail.csv"
    if not coverage_path.exists():
        return pd.DataFrame(), pd.DataFrame(
            [{"source": "venue_coverage_detail.csv", "status": "missing_file", "path": str(coverage_path), "rows": 0}]
        )
    use_columns = [
        "venue_id",
        "citibike_nearest_distance_m",
        "mta_nearest_distance_m",
        "traffic_nearest_distance_m",
        "citibike_covered_200m",
        "mta_covered_200m",
        "traffic_covered_500m",
    ]
    raw = pd.read_csv(coverage_path, usecols=lambda c: c in use_columns)
    coverage = raw[use_columns].copy()
    audit = pd.DataFrame(
        [{"source": "venue_coverage_detail.csv", "status": "ok", "path": str(coverage_path), "rows": len(coverage)}]
    )
    return coverage, audit


def build_urban_activity_spatial_features(paths: PipelinePaths, healthcare: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """构建 v1 城市活动空间代理特征，输出 urban_activity_spatial_features_v1.csv。

    公式: urban_activity_spatial_score = 0.4*citibike_score + 0.4*mta_score + 0.2*traffic_score
    其中 score = max(0, 100*(1 - distance_m/500))，缺失距离记为 0 分。
    """
    coverage, coverage_audit = load_venue_coverage_features(paths)
    if coverage.empty:
        empty = healthcare[["venue_id"]].copy()
        for col in [
            "citibike_nearest_distance_m", "mta_nearest_distance_m", "traffic_nearest_distance_m",
            "citibike_covered_200m", "mta_covered_200m", "traffic_covered_500m",
            "urban_activity_spatial_score",
        ]:
            empty[col] = np.nan
        return empty, coverage_audit

    merged = healthcare[["venue_id"]].merge(coverage, on="venue_id", how="left")
    for col in ["citibike_covered_200m", "mta_covered_200m", "traffic_covered_500m"]:
        if col in merged.columns:
            merged[col] = merged[col].astype(float)

    def _distance_score(series: pd.Series) -> pd.Series:
        """距离转 score：0-200m=100分，200-500m=40-100分，>500m=0分，缺失=0分"""
        score = (1 - series.fillna(500) / 500).clip(lower=0) * 100
        return score

    def _distance_bin(series: pd.Series) -> pd.Series:
        """距离分箱：<200m=3, 200-500m=2, 500-1000m=1, >1000m/缺失=0"""
        bins = pd.cut(
            series.fillna(1500),  # 缺失值视为超远距离
            bins=[0, 200, 500, 1000, float('inf')],
            labels=[3, 2, 1, 0],
            right=True
        )
        return bins.astype(float)

    # 原始距离特征
    merged["citibike_nearest_distance_m"] = merged["citibike_nearest_distance_m"]
    merged["mta_nearest_distance_m"] = merged["mta_nearest_distance_m"]
    merged["traffic_nearest_distance_m"] = merged["traffic_nearest_distance_m"]

    # 分箱特征（用于模型）
    merged["citibike_distance_bin"] = _distance_bin(merged["citibike_nearest_distance_m"])
    merged["mta_distance_bin"] = _distance_bin(merged["mta_nearest_distance_m"])
    merged["traffic_distance_bin"] = _distance_bin(merged["traffic_nearest_distance_m"])

    # score 特征（用于综合评分）
    citibike_score = _distance_score(merged["citibike_nearest_distance_m"])
    mta_score = _distance_score(merged["mta_nearest_distance_m"])
    traffic_score = _distance_score(merged["traffic_nearest_distance_m"])
    merged["urban_activity_spatial_score"] = (0.4 * citibike_score + 0.4 * mta_score + 0.2 * traffic_score).round(2)

    audit = coverage_audit.copy()
    audit["venues_total"] = len(merged)
    audit["venues_with_coverage_data"] = int(merged["citibike_nearest_distance_m"].notna().sum())
    return merged, audit


def load_nys_health_facilities(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载 NYS 医疗设施 CSV → facility_id, name, type, level, lat, lon。"""
    path = paths.data_source_dir / "Health_Facility_General_Information_20260526.csv"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame(
            [{"source": "NYS Health Facility General Information", "status": "missing_file", "path": str(path), "rows": 0}]
        )
    raw = pd.read_csv(path)
    facilities = raw.rename(
        columns={
            "Facility ID": "nys_facility_id",
            "Facility Name": "external_name",
            "Short Description": "facility_short_type",
            "Description": "facility_level",
            "Ownership Type": "ownership_type",
            "Facility Latitude": "latitude",
            "Facility Longitude": "longitude",
            "Facility Address 1": "external_address",
            "Facility City": "external_city",
            "Facility Zip Code": "external_zip",
        }
    )[
        [
            "nys_facility_id",
            "external_name",
            "facility_short_type",
            "facility_level",
            "ownership_type",
            "latitude",
            "longitude",
            "external_address",
            "external_city",
            "external_zip",
        ]
    ].dropna(subset=["latitude", "longitude"])
    facilities = filter_nyc_points(facilities)
    return facilities, pd.DataFrame(
        [{"source": "NYS Health Facility General Information", "status": "ok", "path": str(path), "rows": len(facilities)}]
    )


def load_nys_bed_capacity(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载 NYS 医院床位容量 CSV，取每个 facility 最新记录 → capacity, icu_capacity。"""
    path = paths.data_source_dir / "NYS_Hospital_Bed_Capacity_latest.csv"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame(
            [{"source": "NYS 2dbc-sqe7 bed capacity", "status": "missing_file", "path": str(path), "rows": 0}]
        )
    raw = pd.read_csv(path)
    raw["as_of_date"] = pd.to_datetime(raw["as_of_date"], errors="coerce")
    latest = (
        raw.sort_values("as_of_date")
        .dropna(subset=["facility_pfi"])
        .groupby("facility_pfi", as_index=False)
        .tail(1)
        .rename(
            columns={
                "facility_pfi": "nys_facility_id",
                "total_staffed_acute_care": "capacity",
                "total_staffed_icu_beds": "icu_capacity",
            }
        )
    )
    latest["nys_facility_id"] = latest["nys_facility_id"].astype(str)
    audit = pd.DataFrame(
        [
            {
                "source": "NYS 2dbc-sqe7 bed capacity",
                "status": "ok",
                "path": str(path),
                "rows": len(latest),
                "latest_as_of_date": str(latest["as_of_date"].max().date()) if latest["as_of_date"].notna().any() else pd.NA,
            }
        ]
    )
    return latest[["nys_facility_id", "facility_name", "as_of_date", "capacity", "icu_capacity"]], audit


def load_cms_hospitals(paths: PipelinePaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载 CMS 医院信息 CSV（仅 NY 州）→ hospital_type, rating, ownership 等。"""
    path = paths.data_source_dir / "CMS_Hospital_General_Information.csv"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame(
            [{"source": "CMS xubh-q36u Hospital General Information", "status": "missing_file", "path": str(path), "rows": 0}]
        )
    raw = pd.read_csv(path)
    cms = raw[raw["State"].eq("NY")].rename(
        columns={
            "Facility ID": "cms_facility_id",
            "Facility Name": "cms_facility_name",
            "Hospital Type": "cms_hospital_type",
            "Hospital overall rating": "cms_rating",
            "Hospital Ownership": "cms_ownership",
            "Emergency Services": "cms_emergency_services",
        }
    )[["cms_facility_id", "cms_facility_name", "cms_hospital_type", "cms_rating", "cms_ownership", "cms_emergency_services"]]
    return cms, pd.DataFrame(
        [{"source": "CMS xubh-q36u Hospital General Information", "status": "ok", "path": str(path), "rows": len(cms)}]
    )


def build_capacity_features(paths: PipelinePaths, healthcare: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    facilities, facility_audit = load_nys_health_facilities(paths)
    capacity, capacity_audit = load_nys_bed_capacity(paths)
    cms, cms_audit = load_cms_hospitals(paths)
    facility_points = facilities[["latitude", "longitude"]].to_numpy(dtype=float) if len(facilities) else np.empty((0, 2))

    features: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for _, venue in healthcare.iterrows():
        feature = {
            "venue_id": venue["venue_id"],
            "capacity": np.nan,
            "icu_capacity": np.nan,
            "capacity_as_of_date": pd.NA,
            "capacity_source": pd.NA,
            "facility_level": pd.NA,
            "facility_short_type": pd.NA,
            "cms_hospital_type": pd.NA,
            "cms_rating": np.nan,
            "hospital_level_source": pd.NA,
            "has_capacity_feature": 0,
            "has_hospital_level_feature": 0,
        }
        audit = {
            "venue_id": venue["venue_id"],
            "venue_name": venue.get("name"),
            "nys_facility_id": pd.NA,
            "external_name": pd.NA,
            "match_distance_m": np.nan,
            "name_similarity": np.nan,
            "match_confidence": "no_match",
            "match_status": "no_facility_within_200m",
            "cms_match_status": pd.NA,
        }
        if pd.isna(venue.get("latitude")) or pd.isna(venue.get("longitude")) or len(facility_points) == 0:
            audit["match_status"] = "venue_missing_coordinates" if len(facility_points) else "facility_source_empty"
            features.append(feature)
            audits.append(audit)
            continue
        distances = haversine_distance_m(float(venue["latitude"]), float(venue["longitude"]), facility_points[:, 0], facility_points[:, 1])
        idx = np.where(distances <= 200)[0]
        if len(idx):
            candidates = facilities.iloc[idx].copy()
            candidates["match_distance_m"] = distances[idx]
            candidates["name_similarity"] = candidates["external_name"].map(lambda value: name_similarity(venue.get("name"), value))
            best = candidates.sort_values(["name_similarity", "match_distance_m"], ascending=[False, True]).iloc[0]
            nys_id = str(best.get("nys_facility_id"))
            confidence = "high" if best["name_similarity"] >= 0.75 else "medium" if best["name_similarity"] >= 0.45 else "low"
            feature.update(
                {
                    "facility_level": best.get("facility_level"),
                    "facility_short_type": best.get("facility_short_type"),
                    "hospital_level_source": "NYS Health Facility General Information",
                    "has_hospital_level_feature": 1,
                }
            )
            audit.update(
                {
                    "nys_facility_id": nys_id,
                    "external_name": best.get("external_name"),
                    "match_distance_m": round(float(best["match_distance_m"]), 1),
                    "name_similarity": round(float(best["name_similarity"]), 3),
                    "match_confidence": confidence,
                    "match_status": "matched_by_distance_and_name",
                }
            )
            if not capacity.empty:
                cap_match = capacity[capacity["nys_facility_id"].eq(nys_id)]
                if not cap_match.empty:
                    cap = cap_match.iloc[0]
                    feature.update(
                        {
                            "capacity": cap.get("capacity"),
                            "icu_capacity": cap.get("icu_capacity"),
                            "capacity_as_of_date": cap.get("as_of_date"),
                            "capacity_source": "NYS 2dbc-sqe7",
                            "has_capacity_feature": int(pd.notna(cap.get("capacity"))),
                        }
                    )
            if not cms.empty:
                scores = cms["cms_facility_name"].map(lambda value: name_similarity(best.get("external_name"), value))
                best_idx = scores.idxmax()
                if scores.loc[best_idx] >= 0.72:
                    cms_best = cms.loc[best_idx]
                    feature.update({"cms_hospital_type": cms_best["cms_hospital_type"], "cms_rating": cms_best["cms_rating"]})
                    audit.update(
                        {
                            "cms_facility_id": cms_best["cms_facility_id"],
                            "cms_facility_name": cms_best["cms_facility_name"],
                            "cms_name_similarity": round(float(scores.loc[best_idx]), 3),
                            "cms_match_status": "matched_by_name_ny_only",
                        }
                    )
                else:
                    audit["cms_match_status"] = "no_high_confidence_name_match"
        features.append(feature)
        audits.append(audit)

    source_audit = pd.concat([facility_audit, capacity_audit, cms_audit], ignore_index=True)
    return pd.DataFrame(features), pd.DataFrame(audits), source_audit


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["is_weekend"] = out["day_of_week"].isin(["saturday", "sunday"])
    if "is_business_hours" not in out.columns:
        out["is_business_hours"] = pd.NA
    if "hours_status" not in out.columns:
        out["hours_status"] = "unknown"
    return out


def assign_group_split(groups: pd.Series, seed: int = 42) -> pd.Series:
    """按 prediction_group_id 分组切分 train/val/test（70/15/15），防止同一 Place 的数据泄漏到不同 split。"""
    unique = pd.Series(groups.dropna().unique()).sample(frac=1, random_state=seed).reset_index(drop=True)
    n = len(unique)
    train = set(unique.iloc[: int(n * 0.70)])
    val = set(unique.iloc[int(n * 0.70) : int(n * 0.85)])
    return groups.map(lambda group: "train" if group in train else "val" if group in val else "test")


def build_training_frame(
    labels: pd.DataFrame,
    popular_times: pd.DataFrame,
    place_features: pd.DataFrame,
    spatial_features: pd.DataFrame,
    capacity_features: pd.DataFrame,
    urban_activity_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    healthcare = labels[labels["venue_type"].eq("healthcare")].copy()
    venue_group_map = (
        healthcare[healthcare["serpapi_place_id"].notna()]
        .assign(prediction_group_id=lambda df: df["serpapi_place_id"])
        [["venue_id", "prediction_group_id", "review_count"]]
    )
    training = add_time_features(popular_times)
    if training.empty:
        return training
    training["busy_level"] = training["busyness_score"].map(derive_busy_level)
    training = training.merge(venue_group_map, on="prediction_group_id", how="left").merge(place_features, on="prediction_group_id", how="left")
    training = training.merge(spatial_features, on="venue_id", how="left")
    training = training.merge(
        capacity_features[
            [
                "venue_id",
                "capacity",
                "icu_capacity",
                "facility_level",
                "facility_short_type",
                "cms_hospital_type",
                "cms_rating",
                "has_capacity_feature",
                "has_hospital_level_feature",
            ]
        ],
        on="venue_id",
        how="left",
    )
    if urban_activity_features is not None and not urban_activity_features.empty:
        training = training.merge(urban_activity_features, on="venue_id", how="left")
    training["split"] = assign_group_split(training["prediction_group_id"])
    return training


def build_seasonal_baseline(training: pd.DataFrame) -> pd.DataFrame:
    if training.empty:
        return pd.DataFrame(columns=["district", "day_of_week", "hour", "baseline_score"])
    train = training[training["split"].eq("train")]
    return (
        train.groupby(["district", "day_of_week", "hour"], dropna=False)["busyness_score"]
        .mean()
        .reset_index()
        .rename(columns={"busyness_score": "baseline_score"})
    )


STATIC_FEATURE_COLS = [
        "review_count",
        "district",
        "rating",
        "opening_hours",
        "healthcare_subtype",
        "facility_type",
        "mapped_venue_count",
        "mean_review_count",
        "mean_rating",
        "nearest_subway_distance_m",
        "nearest_citibike_distance_m",
        "poi_density_300m",
        "accessible_status",
        "capacity",
        "icu_capacity",
        "facility_level",
        "facility_short_type",
        "cms_hospital_type",
        "cms_rating",
        "is_business_hours",
        "hours_status",
        "citibike_nearest_distance_m",
        "mta_nearest_distance_m",
        "traffic_nearest_distance_m",
        "citibike_covered_200m",
        "mta_covered_200m",
        "traffic_covered_500m",
        "urban_activity_spatial_score",
]

TRAINING_ROW_FEATURE_COLS = [
    "day_of_week",
    "hour",
    "is_weekend",
    "traffic_score",
    "is_business_hours",
    "month",
    "is_holiday_or_event",
    "mta_hourly_ridership",
    "citibike_station_activity",
    "nyc_traffic_hourly_volume",
    "urban_activity_proxy_score",
    "weather_condition",
    "precipitation_mm",
    "temperature_c",
    "heat_alert",
    "transit_disruption_count",
    "recent_user_report_count",
    "live_capacity_or_wait_time",
]

FEATURE_COVERAGE_SPECS = {
    "day_of_week": ("training_row", "day_of_week"),
    "hour": ("training_row", "hour"),
    "is_weekend": ("training_row", "is_weekend"),
    "review_count": ("venue_static", "review_count"),
    "district": ("venue_static", "district"),
    "rating": ("venue_static", "rating"),
    "healthcare_subtype": ("venue_static", "healthcare_subtype"),
    "opening_hours": ("venue_static", "opening_hours"),
    "facility_type": ("venue_static", "facility_type"),
    "traffic_score": ("training_row", "busyness_score"),
    "nearest_subway_distance_m": ("venue_static", "nearest_subway_distance_m"),
    "nearest_citibike_distance_m": ("venue_static", "nearest_citibike_distance_m"),
    "poi_density_300m": ("venue_static", "poi_density_300m"),
    "capacity": ("venue_static", "capacity"),
    "hospital_level": ("venue_static", "facility_level"),
    "is_business_hours": ("training_row", "is_business_hours"),
    "mapped_venue_count": ("venue_static", "mapped_venue_count"),
    "citibike_nearest_distance_m": ("venue_static", "citibike_nearest_distance_m"),
    "mta_nearest_distance_m": ("venue_static", "mta_nearest_distance_m"),
    "traffic_nearest_distance_m": ("venue_static", "traffic_nearest_distance_m"),
    "citibike_covered_200m": ("venue_static", "citibike_covered_200m"),
    "mta_covered_200m": ("venue_static", "mta_covered_200m"),
    "traffic_covered_500m": ("venue_static", "traffic_covered_500m"),
    "urban_activity_spatial_score": ("venue_static", "urban_activity_spatial_score"),
    "citibike_distance_bin": ("venue_static", "citibike_distance_bin"),
    "mta_distance_bin": ("venue_static", "mta_distance_bin"),
    "traffic_distance_bin": ("venue_static", "traffic_distance_bin"),
    "month": ("training_row", "month"),
    "is_holiday_or_event": ("training_row", "is_holiday_or_event"),
    "mta_hourly_ridership": ("training_row", "mta_hourly_ridership"),
    "citibike_station_activity": ("training_row", "citibike_station_activity"),
    "nyc_traffic_hourly_volume": ("training_row", "nyc_traffic_hourly_volume"),
    "urban_activity_proxy_score": ("training_row", "urban_activity_proxy_score"),
    "weather_condition": ("training_row", "weather_condition"),
    "precipitation_mm": ("training_row", "precipitation_mm"),
    "temperature_c": ("training_row", "temperature_c"),
    "heat_alert": ("training_row", "heat_alert"),
    "transit_disruption_count": ("training_row", "transit_disruption_count"),
    "recent_user_report_count": ("training_row", "recent_user_report_count"),
    "live_capacity_or_wait_time": ("training_row", "live_capacity_or_wait_time"),
}


def infer_feature_dtype(frame: pd.DataFrame, feature: str) -> str:
    if feature not in frame.columns:
        return "missing"
    dtype = frame[feature].dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "bool"
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    return "category"


def summarize_feature_coverage(frame: pd.DataFrame, feature_cols: list[str], scope: str) -> pd.DataFrame:
    """统计指定特征列的非空率（coverage_pct）。"""
    rows = []
    denom = len(frame)
    for col in feature_cols:
        if col not in frame.columns:
            rows.append(
                {
                    "feature": col,
                    "scope": scope,
                    "dtype": "missing",
                    "non_null_rows": 0,
                    "total_rows": denom,
                    "coverage_pct": 0.0,
                    "status": "missing_column",
                }
            )
            continue
        non_null = int(frame[col].notna().sum())
        rows.append(
            {
                "feature": col,
                "scope": scope,
                "dtype": infer_feature_dtype(frame, col),
                "non_null_rows": non_null,
                "total_rows": denom,
                "coverage_pct": round(non_null / denom * 100, 1) if denom else 0.0,
                "status": "ok" if non_null else "all_null",
            }
        )
    return pd.DataFrame(rows)


def summarize_single_feature(frame: pd.DataFrame, feature: str, source_col: str, scope: str) -> dict:
    denom = len(frame)
    basis = "unique healthcare venue" if scope == "venue_static" else "training row"
    if source_col not in frame.columns:
        return {
            "feature": feature,
            "scope": scope,
            "dtype": "missing",
            "non_null_rows": 0,
            "total_rows": denom,
            "coverage_pct": 0.0,
            "status": "missing_column",
            "coverage_basis": basis,
            "source_column": source_col,
        }
    non_null = int(frame[source_col].notna().sum())
    return {
        "feature": feature,
        "scope": scope,
        "dtype": infer_feature_dtype(frame, source_col),
        "non_null_rows": non_null,
        "total_rows": denom,
        "coverage_pct": round(non_null / denom * 100, 1) if denom else 0.0,
        "status": "ok" if non_null else "all_null",
        "coverage_basis": basis,
        "source_column": source_col,
    }


def build_registered_feature_coverage(
    registry: pd.DataFrame,
    training: pd.DataFrame,
    venue_features: pd.DataFrame,
) -> pd.DataFrame:
    """Coverage for the registered model/input features only."""
    frames = {"training_row": training, "venue_static": venue_features}
    rows = []
    registry_meta = registry.set_index("feature")[["group", "priority", "release_stage", "status"]]
    for feature in registry["feature"]:
        scope, source_col = FEATURE_COVERAGE_SPECS.get(feature, ("training_row", feature))
        row = summarize_single_feature(frames[scope], feature, source_col, scope)
        meta = registry_meta.loc[feature].to_dict()
        row.update(
            {
                "group": meta["group"],
                "priority": meta["priority"],
                "release_stage": meta["release_stage"],
                "implementation_status": meta["status"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_training_row_feature_coverage(training: pd.DataFrame) -> pd.DataFrame:
    """训练行级覆盖率：仅统计随 Popular Times 小时样本变化的字段。"""
    rows = []
    for feature in TRAINING_ROW_FEATURE_COLS:
        _, source_col = FEATURE_COVERAGE_SPECS.get(feature, ("training_row", feature))
        rows.append(summarize_single_feature(training, feature, source_col, "training_row"))
    return pd.DataFrame(rows)


def build_venue_static_feature_frame(
    labels: pd.DataFrame,
    place_features: pd.DataFrame,
    spatial_features: pd.DataFrame,
    capacity_features: pd.DataFrame,
    urban_activity_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """合成一行一个 healthcare venue 的静态特征表，用于 venue 级覆盖率。"""
    healthcare = labels[labels["venue_type"].eq("healthcare")].copy()
    venue_group_map = healthcare[["venue_id", "serpapi_place_id", "review_count"]].rename(
        columns={"serpapi_place_id": "prediction_group_id"}
    )
    venue_frame = venue_group_map.merge(place_features, on="prediction_group_id", how="left")
    venue_frame = venue_frame.merge(spatial_features, on="venue_id", how="left")
    venue_frame = venue_frame.merge(
        capacity_features[
            [
                "venue_id",
                "capacity",
                "icu_capacity",
                "facility_level",
                "facility_short_type",
                "cms_hospital_type",
                "cms_rating",
                "has_capacity_feature",
                "has_hospital_level_feature",
            ]
        ],
        on="venue_id",
        how="left",
    )
    if urban_activity_features is not None and not urban_activity_features.empty:
        venue_frame = venue_frame.merge(urban_activity_features, on="venue_id", how="left")
    return venue_frame.drop_duplicates("venue_id", keep="last")


def build_venue_static_feature_coverage(venue_features: pd.DataFrame) -> pd.DataFrame:
    """Venue 级静态覆盖率：一行一个 healthcare venue，不按 7 天小时样本重复计数。"""
    return summarize_feature_coverage(venue_features, STATIC_FEATURE_COLS, scope="venue_static")


def build_training_summary(training: pd.DataFrame) -> pd.DataFrame:
    """输出训练集摘要指标：行数、分组数、venue 数、score 范围、split 分布。"""
    if training.empty:
        return pd.DataFrame([{"metric": "training_rows", "value": 0}])
    rows = [
        {"metric": "training_rows", "value": len(training)},
        {"metric": "unique_prediction_groups", "value": training["prediction_group_id"].nunique()},
        {"metric": "unique_venues", "value": training["venue_id"].nunique()},
        {"metric": "busyness_score_min", "value": training["busyness_score"].min()},
        {"metric": "busyness_score_max", "value": training["busyness_score"].max()},
    ]
    for split, count in training["split"].value_counts(dropna=False).items():
        rows.append({"metric": f"split_rows_{split}", "value": count})
    return pd.DataFrame(rows)


def build_io_dictionary() -> pd.DataFrame:
    """返回 I/O 字段字典：每个字段的 role（input_key/input_feature/target/model_output）和描述。"""
    return pd.DataFrame(
        [
            {"field": "prediction_group_id", "role": "input_key", "source_group": "label_anchor", "description": "SerpAPI place id used as leakage-safe group key"},
            {"field": "venue_id", "role": "input_key", "source_group": "db_key", "description": "DB venue identifier mapped to a prediction group"},
            {"field": "day_of_week", "role": "input_feature", "source_group": "popular_times", "description": "Typical weekday from Google Popular Times cache"},
            {"field": "hour", "role": "input_feature", "source_group": "popular_times", "description": "Hour of day, 0-23"},
            {"field": "review_count", "role": "input_feature", "source_group": "serpapi_label", "description": "SerpAPI review count used as venue visibility proxy"},
            {"field": "district", "role": "input_feature", "source_group": "db_direct", "description": "venues.district"},
            {"field": "rating", "role": "input_feature", "source_group": "db_direct", "description": "venues.rating, backfilled from SerpAPI Place results"},
            {"field": "healthcare_subtype", "role": "input_feature", "source_group": "db_direct", "description": "healthcare_profiles.healthcare_category"},
            {"field": "opening_hours", "role": "input_feature", "source_group": "db_direct", "description": "venues.opening_hours"},
            {"field": "nearest_subway_distance_m", "role": "input_feature", "source_group": "db_spatial", "description": "Distance to nearest MTA subway station in meters"},
            {"field": "nearest_citibike_distance_m", "role": "input_feature", "source_group": "db_spatial", "description": "Distance to nearest Citi Bike station in meters"},
            {"field": "poi_density_300m", "role": "input_feature", "source_group": "db_spatial", "description": "Count of DB healthcare points plus pedestrian_ramps within 300m"},
            {"field": "mapped_venue_count", "role": "input_feature", "source_group": "serpapi_label", "description": "Number of DB venues mapped to the same SerpAPI place id"},
            {"field": "mean_review_count", "role": "input_feature", "source_group": "serpapi_label", "description": "Mean review_count across mapped venues"},
            {"field": "mean_rating", "role": "input_feature", "source_group": "serpapi_label", "description": "Mean DB/SerpAPI rating across mapped venues"},
            {"field": "capacity", "role": "input_feature_optional", "source_group": "external_static", "description": "Latest NYS staffed acute care bed capacity where matched"},
            {"field": "icu_capacity", "role": "input_feature_optional", "source_group": "external_static", "description": "Latest NYS staffed ICU bed capacity where matched"},
            {"field": "facility_level", "role": "input_feature_optional", "source_group": "external_static", "description": "NYS facility description / hospital level proxy"},
            {"field": "facility_short_type", "role": "input_feature_optional", "source_group": "external_static", "description": "NYS facility short type"},
            {"field": "cms_hospital_type", "role": "input_feature_optional", "source_group": "external_static", "description": "CMS hospital type"},
            {"field": "cms_rating", "role": "input_feature_optional", "source_group": "external_static", "description": "CMS hospital overall rating"},
            {
                "field": "is_business_hours",
                "role": "postprocess_constraint",
                "source_group": "derived",
                "description": "Whether day_of_week + hour falls inside parsed hours; use for serving truncation/fallback, not as a core model driver",
            },
            {"field": "hours_status", "role": "input_feature_audit", "source_group": "derived", "description": "parsed/open_24h/closed/unknown status for opening-hours parsing"},
            {"field": "busyness_score", "role": "target", "source_group": "label_only", "description": "Google Popular Times weak-label target, 0-100"},
            {"field": "busy_level", "role": "target_class", "source_group": "derived", "description": "Derived quiet/moderate/busy class from busyness_score"},
            {"field": "predicted_score", "role": "model_output", "source_group": "model_output", "description": "Future model output score, 0-100"},
            {
                "field": "predicted_level",
                "role": "model_output",
                "source_group": "model_output",
                "description": "quiet/moderate/busy derived from predicted_score; no_data is display fallback when no prediction is available or venue is outside business hours",
            },
            {
                "field": "serving_predicted_level",
                "role": "serving_output",
                "source_group": "model_output",
                "description": "Frontend-facing level after applying hours constraint: outside business hours -> no_data",
            },
            {"field": "prediction_confidence", "role": "model_output", "source_group": "model_output", "description": "Future confidence output for frontend display"},
            {"field": "citibike_nearest_distance_m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Distance to nearest Citi Bike station from venue_coverage_detail.csv (meters)"},
            {"field": "mta_nearest_distance_m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Distance to nearest MTA stop from venue_coverage_detail.csv (meters)"},
            {"field": "traffic_nearest_distance_m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Distance to nearest NYC Traffic segment from venue_coverage_detail.csv (meters)"},
            {"field": "citibike_covered_200m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Boolean: Citi Bike station within 200m"},
            {"field": "mta_covered_200m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Boolean: MTA stop within 200m"},
            {"field": "traffic_covered_500m", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Boolean: NYC Traffic segment within 500m"},
            {"field": "urban_activity_spatial_score", "role": "input_feature", "source_group": "urban_activity_spatial", "description": "Composite v1 spatial urban activity proxy: 0.4*citibike + 0.4*mta + 0.2*traffic distance scores"},
            {"field": "mta_hourly_ridership", "role": "input_feature_optional", "source_group": "urban_activity_hourly_v2", "description": "v2 placeholder: hourly MTA ridership index"},
            {"field": "citibike_station_activity", "role": "input_feature_optional", "source_group": "urban_activity_hourly_v2", "description": "v2 placeholder: hourly Citi Bike station activity index"},
            {"field": "nyc_traffic_hourly_volume", "role": "input_feature_optional", "source_group": "urban_activity_hourly_v2", "description": "v2 placeholder: hourly NYC traffic volume index"},
            {"field": "urban_activity_proxy_score", "role": "input_feature_optional", "source_group": "urban_activity_hourly_v2", "description": "v2 placeholder: composite hourly urban activity proxy score"},
        ]
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def count_csv_rows(path: Path) -> int:
    """快速统计 CSV 行数（不读入内存），用于 manifest。"""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="ignore") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def run_pipeline(project_root: Path | None = None) -> dict[str, Path]:
    """主函数：执行完整管线，输出特征、模型、评估、消融与 manifest。返回 {name: path} 字典。"""
    paths = default_paths(project_root)
    paths.notebook_output_dir.mkdir(parents=True, exist_ok=True)
    labels = read_labels(paths)
    healthcare = labels[labels["venue_type"].eq("healthcare")].copy()

    status_breakdown, coverage_summary = build_coverage_summary(labels)
    registry = build_feature_registry()
    popular_times, popular_summary = build_popular_times(paths)
    place_features = build_place_features(labels)
    spatial_features, spatial_audit = build_spatial_features(paths, healthcare)
    urban_activity_features, urban_activity_audit = build_urban_activity_spatial_features(paths, healthcare)
    capacity_features, capacity_match_audit, capacity_source_audit = build_capacity_features(paths, healthcare)
    db_feature_source_audit = load_db_feature_source_audit(paths)
    training = build_training_frame(labels, popular_times, place_features, spatial_features, capacity_features, urban_activity_features)
    venue_static_features = build_venue_static_feature_frame(
        labels, place_features, spatial_features, capacity_features, urban_activity_features
    )
    baseline = build_seasonal_baseline(training)
    feature_coverage = build_registered_feature_coverage(registry, training, venue_static_features)
    training_row_feature_coverage = build_training_row_feature_coverage(training)
    venue_feature_coverage = build_venue_static_feature_coverage(venue_static_features)
    training_summary = build_training_summary(training)
    io_dictionary = build_io_dictionary()
    model_metrics, model_predictions, prediction_curve = evaluate_model_family(
        training, build_model_feature_blocks()["full_available"], family_name="full_available"
    )
    ablation_summary = build_ablation_summary(training)
    low_coverage_imputation = build_low_coverage_imputation_diagnostics(training)
    low_coverage_drop_one = build_low_coverage_drop_one_ablation(training)

    outputs = {
        "status_breakdown": paths.notebook_output_dir / "label_status_breakdown.csv",
        "coverage_summary": paths.notebook_output_dir / "coverage_summary.csv",
        "feature_registry": paths.notebook_output_dir / "feature_registry.csv",
        "popular_times": paths.notebook_output_dir / "popular_times_hourly_rows.csv",
        "popular_times_summary": paths.notebook_output_dir / "popular_times_summary.csv",
        "place_features": paths.notebook_output_dir / "place_features.csv",
        "spatial_features": paths.notebook_output_dir / "spatial_features_v1.csv",
        "spatial_audit": paths.notebook_output_dir / "spatial_features_v1_audit.csv",
        "urban_activity_features": paths.notebook_output_dir / "urban_activity_spatial_features_v1.csv",
        "urban_activity_audit": paths.notebook_output_dir / "urban_activity_spatial_features_v1_audit.csv",
        "capacity_features": paths.notebook_output_dir / "healthcare_capacity_level_features_v1.csv",
        "capacity_match_audit": paths.notebook_output_dir / "healthcare_external_match_audit_v1.csv",
        "capacity_source_audit": paths.notebook_output_dir / "healthcare_external_source_audit_v1.csv",
        "db_feature_source_audit": paths.notebook_output_dir / "db_feature_source_audit.csv",
        "training_frame": paths.notebook_output_dir / "ml_training_frame_v1.csv",
        "training_summary": paths.notebook_output_dir / "training_frame_summary.csv",
        "feature_coverage": paths.notebook_output_dir / "feature_coverage_summary.csv",
        "training_row_feature_coverage": paths.notebook_output_dir / "training_row_feature_coverage_summary.csv",
        "venue_feature_coverage": paths.notebook_output_dir / "venue_static_feature_coverage_summary.csv",
        "seasonal_baseline": paths.notebook_output_dir / "seasonal_baseline.csv",
        "io_dictionary": paths.notebook_output_dir / "input_output_field_dictionary.csv",
        "model_metrics": paths.notebook_output_dir / "model_metrics_v1.csv",
        "model_predictions": paths.notebook_output_dir / "model_test_predictions_v1.csv",
        "prediction_curve": paths.notebook_output_dir / "prediction_curve_v1.csv",
        "ablation_summary": paths.notebook_output_dir / "ablation_summary_v1.csv",
        "low_coverage_imputation": paths.notebook_output_dir / "low_coverage_imputation_diagnostics_v1.csv",
        "low_coverage_drop_one": paths.notebook_output_dir / "low_coverage_drop_one_ablation_v1.csv",
    }
    for key, frame in {
        "status_breakdown": status_breakdown,
        "coverage_summary": coverage_summary,
        "feature_registry": registry,
        "popular_times": popular_times,
        "popular_times_summary": popular_summary,
        "place_features": place_features,
        "spatial_features": spatial_features,
        "spatial_audit": spatial_audit,
        "urban_activity_features": urban_activity_features,
        "urban_activity_audit": urban_activity_audit,
        "capacity_features": capacity_features,
        "capacity_match_audit": capacity_match_audit,
        "capacity_source_audit": capacity_source_audit,
        "db_feature_source_audit": db_feature_source_audit,
        "training_frame": training,
        "training_summary": training_summary,
        "feature_coverage": feature_coverage,
        "training_row_feature_coverage": training_row_feature_coverage,
        "venue_feature_coverage": venue_feature_coverage,
        "seasonal_baseline": baseline,
        "io_dictionary": io_dictionary,
        "model_metrics": model_metrics,
        "model_predictions": model_predictions,
        "prediction_curve": prediction_curve,
        "ablation_summary": ablation_summary,
        "low_coverage_imputation": low_coverage_imputation,
        "low_coverage_drop_one": low_coverage_drop_one,
    }.items():
        write_csv(frame, outputs[key])

    metadata = pd.DataFrame(
        [
            {"name": key, "path": str(path), "rows": count_csv_rows(path)}
            for key, path in outputs.items()
        ]
    )
    metadata_path = paths.notebook_output_dir / "pipeline_outputs_manifest.csv"
    write_csv(metadata, metadata_path)
    outputs["manifest"] = metadata_path
    return outputs


def parse_args() -> argparse.Namespace:
    """CLI 参数解析。支持 --project-root 指定项目根目录。"""
    parser = argparse.ArgumentParser(description="Build healthcare busyness ML feature outputs.")
    parser.add_argument("--project-root", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    """CLI 入口：执行管线并打印 manifest 路径。"""
    args = parse_args()
    outputs = run_pipeline(args.project_root)
    manifest = outputs["manifest"]
    print(f"ML feature pipeline complete: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

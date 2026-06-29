"""Build hourly ML labels from cached SerpAPI Place JSON.

This script does not call SerpAPI. It only reads cached JSON files produced by
the Place API validation step and expands Google Popular Times graph results
into tabular hourly labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DAY_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

#路径解析
def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()

# 计算缓存路径
def phase_b_cache_path(raw_dir: Path, place_id: str) -> Path:
    params = {
        "place_id": str(place_id),
        "type": "place",
        "hl": "en",
        "engine": "google_maps",
    }
    cache_key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    return raw_dir / f"phase_b_place_{cache_key}.json"

#字符串转换为小时
def parse_hour_label(label: str) -> int:
    match = re.fullmatch(r"\s*(\d{1,2})\s*([AP]M)\s*", str(label).upper())
    if not match:
        raise ValueError(f"Unsupported time label: {label!r}")

    hour = int(match.group(1))
    period = match.group(2)
    if hour == 12:
        hour = 0
    if period == "PM":
        hour += 12
    return hour

#解析单个venue的popular times数据(本地json文件)
def iter_popular_time_rows(
    venue_row: pd.Series,
    json_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(json_path.read_text())
    place_results = data.get("place_results") or {}
    popular_times = place_results.get("popular_times") or {}
    graph_results = popular_times.get("graph_results") or {}

    rows: list[dict[str, Any]] = []
    # 输入特征审计
    audit = {
        "venue_id": venue_row["venue_id"],
        "venue_name": venue_row["venue_name"],
        "serpapi_place_id": venue_row["serpapi_place_id"],
        "serpapi_name": venue_row.get("serpapi_name"),
        "source_json_file": json_path.name,
        "has_json": json_path.exists(),
        "has_popular_times": bool(popular_times),
        "days_available": 0,
        "hour_rows": 0,
        "min_hour": None,
        "max_hour": None,
        "parse_status": "ok",
        "parse_error": "",
    }

    try:
        if not isinstance(graph_results, dict) or not graph_results:
            raise ValueError("popular_times.graph_results is empty or not a dict")

        hours: list[int] = []
        for day_name, day_values in graph_results.items():
            day_key = str(day_name).lower()
            if day_key not in DAY_TO_INDEX:
                raise ValueError(f"Unsupported day name: {day_name!r}")
            if not isinstance(day_values, list):
                raise ValueError(f"Day values are not a list for {day_name!r}")

            for item in day_values:
                if not isinstance(item, dict):
                    raise ValueError(f"Hour item is not a dict for {day_name!r}: {item!r}")
                if "time" not in item or "busyness_score" not in item:
                    raise ValueError(f"Missing time/busyness_score for {day_name!r}: {item!r}")

                hour = parse_hour_label(str(item["time"]))
                score = item["busyness_score"]
                if not isinstance(score, int | float):
                    raise ValueError(f"Invalid busyness_score: {score!r}")

                hours.append(hour)
                rows.append({
                    "venue_id": venue_row["venue_id"],
                    "venue_name": venue_row["venue_name"],
                    "serpapi_place_id": venue_row["serpapi_place_id"],
                    "serpapi_name": venue_row.get("serpapi_name"),
                    "day_name": day_key,
                    "day_of_week": DAY_TO_INDEX[day_key],
                    "time_label": item["time"],
                    "hour": hour,
                    "busyness_score": int(score),
                    "busyness_info": item.get("info"),
                    "target_type": "google_popular_times_proxy",
                    "source": "serpapi_place_api_cache",
                    "source_json_file": json_path.name,
                })

        audit["days_available"] = len(graph_results)
        audit["hour_rows"] = len(rows)
        audit["min_hour"] = min(hours) if hours else None
        audit["max_hour"] = max(hours) if hours else None
    except Exception as exc:
        audit["parse_status"] = "error"
        audit["parse_error"] = f"{type(exc).__name__}: {exc}"
        rows = []

    return rows, audit

# 主函数
def build_training_data(
    phase_b_results: Path,
    raw_dir: Path,
    output_labels: Path,
    output_audit: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    phase_b = pd.read_csv(phase_b_results)
    positive = phase_b[phase_b["has_popular_times"].fillna(False).astype(bool)].copy()

    all_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for _, venue_row in positive.iterrows():
        json_path = phase_b_cache_path(raw_dir, str(venue_row["serpapi_place_id"]))
        if not json_path.exists():
            # 记录缺失的json文件
            audit_rows.append({
                "venue_id": venue_row["venue_id"],
                "venue_name": venue_row["venue_name"],
                "serpapi_place_id": venue_row["serpapi_place_id"],
                "serpapi_name": venue_row.get("serpapi_name"),
                "source_json_file": json_path.name,
                "has_json": False,
                "has_popular_times": True,
                "days_available": 0,
                "hour_rows": 0,
                "min_hour": None,
                "max_hour": None,
                "parse_status": "missing_json",
                "parse_error": str(json_path),
            })
            continue

        rows, audit = iter_popular_time_rows(venue_row, json_path)
        all_rows.extend(rows)
        audit_rows.append(audit)

    labels = pd.DataFrame(all_rows)
    audit = pd.DataFrame(audit_rows)

    output_labels.parent.mkdir(parents=True, exist_ok=True)
    output_audit.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(output_labels, index=False)
    audit.to_csv(output_audit, index=False)

    return labels, audit

# CLI参数解析
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build hourly Popular Times ML labels from cached SerpAPI JSON.")
    parser.add_argument(
        # 带有popular times的venue列表
        "--phase-b-results",
        default="../../6.22-6.27/output/phase_b_place_results.csv",
    )
    parser.add_argument(
        # 上述venue列表对应的serpapi place api缓存json文件夹
        "--raw-dir",
        default="../../6.22-6.27/output/serpapi_raw_responses",
    )
    parser.add_argument(
        # 输出标签
        "--output-labels",
        default="../output/populartimes_hourly_labels_phase_b.csv",
    )
    parser.add_argument(
        # 输出审计日志
        "--output-audit",
        default="../output/populartimes_hourly_labels_phase_b_audit.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    labels, audit = build_training_data(
        phase_b_results=resolve_path(args.phase_b_results),
        raw_dir=resolve_path(args.raw_dir),
        output_labels=resolve_path(args.output_labels),
        output_audit=resolve_path(args.output_audit),
    )

    ok_audit = audit[audit["parse_status"].eq("ok")] if not audit.empty else audit
    print("Popular Times training data build complete")
    print(f"  venues_with_popular_times_input: {len(audit)}")
    print(f"  venues_parsed_ok: {len(ok_audit)}")
    print(f"  venues_parse_failed: {len(audit) - len(ok_audit)}")
    print(f"  hourly_label_rows: {len(labels)}")
    if not labels.empty:
        print(f"  unique_venues: {labels['venue_id'].nunique()}")
        print(f"  unique_place_ids: {labels['serpapi_place_id'].nunique()}")
        print(f"  busyness_score_min: {labels['busyness_score'].min()}")
        print(f"  busyness_score_max: {labels['busyness_score'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

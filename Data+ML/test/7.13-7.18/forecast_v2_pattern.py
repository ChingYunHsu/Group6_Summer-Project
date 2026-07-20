"""V2 known-venue pattern model: SerpAPI baseline plus live-context adjustment."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

import db_utils
from score_utils import score_to_level

BASELINE_FEATURES = ["day_of_week", "hour_of_day", "is_weekend", "venue_type", "district", "rating"]
VENUE_SPECIFIC_FEATURES = BASELINE_FEATURES + [
    "venue_id", "latitude", "longitude", "weather_risk", "source_confidence",
    "accessible_status", "active_warning", "open_now", "rating_missing",
]
ENRICHED_FEATURES = VENUE_SPECIFIC_FEATURES + [
    "nyc_traffic_baseline_score", "nyc_traffic_baseline_missing",
]
CATEGORICAL_FEATURES = {"venue_id", "venue_type", "district", "weather_risk", "accessible_status"}
DYNAMIC_COLUMNS = (
    "temperature_c", "precipitation_mm", "relative_humidity_pct", "wind_speed_kmh", "heat_alert",
    "citibike_station_activity", "nearby_bike_availability", "nearby_dock_availability",
    "mta_service_disruption_flag", "mta_realtime_arrival_count_1h",
    "recent_report_count_1h", "recent_report_count_3h", "crowding_report_count_3h",
)
MODEL_VERSION = "forecast-v2-known-venue-serpapi-context"
PUBLISHED_MODEL_VERSION = "forecast-v2"
SPLIT_TYPE = "known_venue_temporal_snapshot"


def venues(ids: list[str]) -> pd.DataFrame:
    marks = ",".join(["%s"] * len(ids))
    return db_utils.read_sql(
        "SELECT venue_id, venue_type, district, rating, latitude, longitude, weather_risk, "
        "source_confidence, accessible_status, active_warning, open_now "
        "FROM venues WHERE venue_id IN (" + marks + ")", tuple(ids)
    )


def traffic_baseline(ids: list[str]) -> pd.DataFrame:
    """Return the 2025 SODA venue-hour traffic profile used by V2.

    These rows are intentionally read from the retained historical baseline,
    not the short-lived current-context model.  The baseline date is irrelevant:
    only the source-derived hour-of-day traffic profile is joined to each label.
    """
    marks = ",".join(["%s"] * len(ids))
    return db_utils.read_sql(
        "SELECT venue_id, HOUR(forecast_start_time) AS hour_of_day, "
        "MAX(score) AS nyc_traffic_baseline_score "
        "FROM busyness_scores "
        "WHERE model_version='nyc_traffic_baseline_v1' AND venue_id IN (" + marks + ") "
        "GROUP BY venue_id, HOUR(forecast_start_time)",
        tuple(ids),
    )


def add_traffic_baseline(frame: pd.DataFrame, traffic: pd.DataFrame) -> pd.DataFrame:
    """Attach the same venue-hour traffic profile to labels and future curve rows."""
    frame = frame.merge(traffic, on=["venue_id", "hour_of_day"], how="left", validate="many_to_one")
    frame["nyc_traffic_baseline_missing"] = frame.nyc_traffic_baseline_score.isna().astype(int)
    frame["nyc_traffic_baseline_score"] = frame.nyc_traffic_baseline_score.fillna(0)
    return frame


def group_split(df: pd.DataFrame):
    """Legacy cold-start split, retained for the separately stored reference output."""
    first = GroupShuffleSplit(n_splits=1, train_size=.7, random_state=42)
    train_i, rest_i = next(first.split(df, groups=df.place_id))
    train, rest = df.iloc[train_i], df.iloc[rest_i]
    second = GroupShuffleSplit(n_splits=1, train_size=.5, random_state=43)
    val_i, test_i = next(second.split(rest, groups=rest.place_id))
    return train, rest.iloc[val_i], rest.iloc[test_i]


def parse_hour(value: str) -> int:
    hour, meridiem = value.strip().split()
    number = int(hour) % 12
    return number + (12 if meridiem.upper() == "PM" else 0)


def load_legacy_labels(path: Path) -> pd.DataFrame:
    legacy = pd.read_csv(path, dtype={"venue_id": str, "place_id": str})
    days = {name: index for index, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))}
    legacy["day_of_week"] = legacy.day.str.lower().map(days)
    legacy["hour_of_day"] = legacy.hour.map(parse_hour)
    return legacy[["venue_id", "place_id", "day_of_week", "hour_of_day", "busyness_score"]].dropna()


def temporal_snapshot_split(legacy: pd.DataFrame, current: pd.DataFrame):
    """Train only on the earlier snapshot; test on the later snapshot's shared venue-hours."""
    key = ["venue_id", "place_id", "day_of_week", "hour_of_day"]
    shared = legacy[key].merge(current[key], on=key, how="inner")
    train = legacy.merge(shared, on=key, how="inner")
    test = current.merge(shared, on=key, how="inner")
    if not set(test.venue_id).issubset(set(train.venue_id)):
        raise ValueError("Temporal test includes a venue absent from the earlier snapshot")
    return train, test


def feature_matrix(df: pd.DataFrame, features: list[str], columns: list[str] | None = None) -> pd.DataFrame:
    x = df[features].copy()
    categoricals = [column for column in features if column in CATEGORICAL_FEATURES]
    x = pd.get_dummies(x, columns=categoricals, dummy_na=True).astype(float)
    x = x.reindex(columns=columns, fill_value=0) if columns is not None else x
    return x.fillna(0)


def metrics(y, predicted) -> dict:
    predicted = np.clip(predicted, 0, 100)
    return {"mae": round(mean_absolute_error(y, predicted), 3),
            "rmse": round(mean_squared_error(y, predicted) ** .5, 3), "r2": round(r2_score(y, predicted), 3)}


def train_variant(name: str, features: list[str], train: pd.DataFrame, test: pd.DataFrame):
    columns = feature_matrix(train, features).columns.tolist()
    model = GradientBoostingRegressor(n_estimators=200, random_state=42).fit(
        feature_matrix(train, features, columns), train.busyness_score
    )
    rows = []
    for split_name, data in (("train", train), ("test", test)):
        rows.append({"model_name": "GradientBoostingRegressor", "model_variant": name,
                     "split_type": SPLIT_TYPE, "split": split_name, "raw_feature_count": len(features),
                     "feature_count": len(columns), **metrics(data.busyness_score, model.predict(feature_matrix(data, features, columns)))})
    return model, columns, rows


def cached_context() -> dict:
    rows = db_utils.read_sql(
        "SELECT context_type, payload_json FROM external_context_cache "
        "WHERE context_type IN ('weather_forecast','gbfs_station_status','mta_realtime') "
        "AND expires_at >= UTC_TIMESTAMP() ORDER BY created_at DESC"
    )
    result = {}
    for row in rows.itertuples(index=False):
        if row.context_type not in result:
            result[row.context_type] = json.loads(row.payload_json) if isinstance(row.payload_json, str) else row.payload_json
    return result


def weather_at(payload: dict, when: pd.Timestamp) -> dict:
    values = {name: payload.get(name, 0) for name in DYNAMIC_COLUMNS[:5]}
    series, times = payload.get("hourly_series", {}), payload.get("hourly_series", {}).get("time", [])
    try:
        index = [pd.Timestamp(value, tz="UTC") for value in times].index(when)
    except (TypeError, ValueError):
        return values
    for target, source in {"temperature_c": "temperature_2m", "precipitation_mm": "precipitation",
                           "relative_humidity_pct": "relative_humidity_2m", "wind_speed_kmh": "wind_speed_10m"}.items():
        hourly = series.get(source, [])
        if index < len(hourly):
            values[target] = hourly[index]
    values["heat_alert"] = int(float(values["temperature_c"] or 0) >= 32)
    return values


def report_context(venue_ids: list[str], now: pd.Timestamp) -> pd.DataFrame:
    marks = ",".join(["%s"] * len(venue_ids))
    query = (
        "SELECT venue_id, SUM(created_at >= %s) AS recent_report_count_1h, "
        "SUM(created_at >= %s) AS recent_report_count_3h, "
        "SUM(created_at >= %s AND issue_type IN ('crowded','queue','wait_time')) AS crowding_report_count_3h "
        "FROM user_reports WHERE status='active' AND venue_id IN (" + marks + ") GROUP BY venue_id"
    )
    return db_utils.read_sql(query, ((now - pd.Timedelta(hours=1)).to_pydatetime(),
                                     (now - pd.Timedelta(hours=3)).to_pydatetime(),
                                     (now - pd.Timedelta(hours=3)).to_pydatetime(), *venue_ids))


def add_dynamic_context(curve: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    context = cached_context()
    weather, gbfs, mta = (context.get("weather_forecast", {}), context.get("gbfs_station_status", {}), context.get("mta_realtime", {}))
    for column in DYNAMIC_COLUMNS:
        curve[column] = 0.0
    for index, when in curve.forecast_for.items():
        for column, value in weather_at(weather, when).items():
            curve.loc[index, column] = value or 0
    for column in DYNAMIC_COLUMNS[5:10]:
        curve[column] = (gbfs if column in gbfs else mta).get(column, 0) or 0
    reports = report_context(curve.venue_id.unique().tolist(), now)
    curve = curve.merge(reports, on="venue_id", how="left", suffixes=("", "_db"))
    for column in DYNAMIC_COLUMNS[-3:]:
        curve[column] = pd.to_numeric(curve.pop(f"{column}_db"), errors="coerce").fillna(0) if f"{column}_db" in curve else 0
    curve["weather_context_available"] = int("weather_forecast" in context)
    curve["gbfs_context_available"] = int("gbfs_station_status" in context)
    curve["mta_context_available"] = int(mta.get("mta_arrival_missing") is False)
    curve["dynamic_context_available"] = int(bool(context))
    curve["dynamic_delta"] = np.clip(
        4 * curve.recent_report_count_1h + 2 * curve.crowding_report_count_3h
        + 6 * curve.mta_service_disruption_flag + np.minimum(curve.precipitation_mm, 8) * .5
        + curve.heat_alert * 2 + np.clip((curve.citibike_station_activity - 2000) / 1000, -2, 2) * 1.5,
        -15, 20,
    ).round(2)
    return curve


def publish_forecasts(curve: pd.DataFrame) -> int:
    """Upsert one generated V2 batch using the backend's stable model-version contract."""
    batch_generated_at = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    rows = []
    for row in curve.itertuples(index=False):
        forecast_for = pd.Timestamp(row.forecast_for).to_pydatetime()
        if forecast_for.tzinfo is not None:
            forecast_for = forecast_for.replace(tzinfo=None)
        rows.append((
            row.venue_id, forecast_for, int(round(row.predicted_score)), row.predicted_level,
            None, PUBLISHED_MODEL_VERSION, batch_generated_at,
        ))
    sql = """
        INSERT INTO busyness_forecasts
            (venue_id, forecast_for, predicted_score, predicted_level,
             estimated_wait_minutes, model_version, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            predicted_score=VALUES(predicted_score),
            predicted_level=VALUES(predicted_level),
            estimated_wait_minutes=VALUES(estimated_wait_minutes),
            generated_at=VALUES(generated_at)
    """
    conn = db_utils.get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hours", type=int, default=12)
    parser.add_argument("--publish", action="store_true",
                        help="Upsert the generated 12-hour curve to busyness_forecasts as forecast-v2")
    args = parser.parse_args()
    current_labels = pd.read_csv(args.labels, dtype={"venue_id": str, "place_id": str})
    legacy_labels = load_legacy_labels(args.legacy_labels)
    ids = sorted(set(current_labels.venue_id) | set(legacy_labels.venue_id))
    static = venues(ids)
    traffic = traffic_baseline(ids)
    def enrich(labels: pd.DataFrame) -> pd.DataFrame:
        frame = labels.merge(static, on="venue_id", how="inner", validate="many_to_one")
        frame["is_weekend"] = (frame.day_of_week >= 5).astype(int)
        frame["rating_missing"] = frame.rating.isna().astype(int)
        return add_traffic_baseline(frame, traffic)
    train, test = temporal_snapshot_split(enrich(legacy_labels), enrich(current_labels))
    baseline_model, baseline_columns, baseline_rows = train_variant("baseline_time", BASELINE_FEATURES, train, test)
    static_model, static_columns, static_rows = train_variant(
        "venue_specific_enriched_baseline", VENUE_SPECIFIC_FEATURES, train, test
    )
    enriched_model, enriched_columns, enriched_rows = train_variant(
        "venue_specific_enriched_with_traffic", ENRICHED_FEATURES, train, test
    )
    static_test_mae = next(row["mae"] for row in static_rows if row["split"] == "test")
    for row in baseline_rows + static_rows + enriched_rows:
        row["mae_improvement_vs_baseline"] = (
            round(static_test_mae - row["mae"], 3) if row["split"] == "test" else None
        )
    results = pd.DataFrame(baseline_rows + static_rows + enriched_rows)
    now = pd.Timestamp(datetime.now(timezone.utc)).floor("h")
    base = enrich(current_labels).drop_duplicates("venue_id")[[
        "venue_id", "place_id", *[field for field in VENUE_SPECIFIC_FEATURES if field != "venue_id"]
    ]]
    future = []
    for offset in range(args.hours):
        target = now + timedelta(hours=offset)
        item = base.copy()
        item["forecast_for"], item["offset_hours"] = target, offset
        item["day_of_week"], item["hour_of_day"], item["is_weekend"] = target.weekday(), target.hour, int(target.weekday() >= 5)
        future.append(item)
    curve = add_traffic_baseline(pd.concat(future, ignore_index=True), traffic)
    curve = add_dynamic_context(curve, now)
    curve["baseline_score"] = np.clip(enriched_model.predict(feature_matrix(curve, ENRICHED_FEATURES, enriched_columns)), 0, 100).round(2)
    curve["predicted_score"] = np.clip(curve.baseline_score + curve.dynamic_delta, 0, 100).round(2)
    curve["predicted_level"], curve["model_version"] = curve.predicted_score.map(score_to_level), MODEL_VERSION
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output_dir / "forecast_v2_pattern_model_metrics.csv", index=False)
    curve.to_csv(args.output_dir / "prediction_curve_v2_pattern.csv", index=False)
    published_rows = publish_forecasts(curve) if args.publish else 0
    (args.output_dir / "forecast_v2_pattern_manifest.json").write_text(json.dumps({
        "model_version": MODEL_VERSION, "target_type": "google_popular_times_proxy", "training_rows": len(train),
        "test_rows": len(test), "venues": test.venue_id.nunique(), "places": test.place_id.nunique(), "split": SPLIT_TYPE,
        "validation_status": "not available: no third temporally complete SerpAPI cohort",
        "baseline_features": BASELINE_FEATURES, "venue_specific_features": VENUE_SPECIFIC_FEATURES,
        "enriched_features": ENRICHED_FEATURES,
        "traffic_feature": {"source": "busyness_scores.nyc_traffic_baseline_v1", "join": "venue_id + hour_of_day",
                            "coverage_pct": round(100 * (1 - train.nyc_traffic_baseline_missing.mean()), 2)},
        "published_model_version": PUBLISHED_MODEL_VERSION if args.publish else None,
        "published_rows": published_rows,
        "excluded_low_coverage_features": ["borough", "opening_hours", "primary_language", "venue_accessibility", "venue_language"],
        "dynamic_context_columns": DYNAMIC_COLUMNS, "dynamic_delta": "auditable serving rule; not supervised until real telemetry is sufficient",
        "cold_start_reference": "../v2_pattern_serpapi_20260716/forecast_v2_pattern_model_metrics.csv",
    }, indent=2))
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()

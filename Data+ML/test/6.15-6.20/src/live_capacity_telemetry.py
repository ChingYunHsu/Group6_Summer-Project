"""Live capacity telemetry ingestion for venue-level busyness rows."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


MODEL_VERSION = "live-telemetry-v1"
DEFAULT_SOURCE_NAME = "live_capacity"
DEFAULT_TTL_SECONDS = 300


class TelemetryValidationError(ValueError):
    """Raised when a live capacity telemetry event cannot be normalized."""


@dataclass(frozen=True)
class NormalizedTelemetryEvent:
    source_name: str
    source_venue_id: str
    observed_at: datetime
    load_percent: int
    avg_wait_minutes: int
    level: str
    forecast_start_time: datetime
    forecast_end_time: datetime
    features_snapshot_id: str
    forecast_1h: str | None


@dataclass(frozen=True)
class BatchIngestionResult:
    received: int
    ingested: int
    rejected: int
    unmatched: list[str]


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if not isinstance(value, str) or not value:
        raise TelemetryValidationError("observed_at is required")
    normalized = value.removesuffix("Z")
    try:
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except ValueError as exc:
        raise TelemetryValidationError("observed_at must be ISO-8601") from exc


def _normalize_int(value: Any, field_name: str, minimum: int, maximum: int | None = None) -> int:
    if value is None:
        raise TelemetryValidationError(f"{field_name} is required")
    try:
        normalized = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise TelemetryValidationError(f"{field_name} must be numeric") from exc
    if normalized < minimum:
        raise TelemetryValidationError(f"{field_name} must be >= {minimum}")
    if maximum is not None and normalized > maximum:
        raise TelemetryValidationError(f"{field_name} must be <= {maximum}")
    return normalized


def level_for_load_percent(load_percent: int) -> str:
    if load_percent <= 35:
        return "quiet"
    if load_percent <= 70:
        return "moderate"
    return "busy"


def _floor_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _snapshot_id(payload: dict[str, Any]) -> str:
    if payload.get("features_snapshot_id"):
        return str(payload["features_snapshot_id"])
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def normalize_event(payload: dict[str, Any]) -> NormalizedTelemetryEvent:
    source_venue_id = payload.get("source_venue_id")
    if not source_venue_id:
        raise TelemetryValidationError("source_venue_id is required")

    source_name = str(payload.get("source_name") or DEFAULT_SOURCE_NAME)
    observed_at = _parse_datetime(payload.get("observed_at"))
    load_percent = _normalize_int(payload.get("load_percent"), "load_percent", 0, 100)
    avg_wait_minutes = _normalize_int(payload.get("avg_wait_minutes"), "avg_wait_minutes", 0)
    ttl_seconds = _normalize_int(payload.get("ttl_seconds", DEFAULT_TTL_SECONDS), "ttl_seconds", 1)
    forecast_start_time = _floor_to_minute(observed_at)
    forecast_end_time = forecast_start_time + timedelta(seconds=ttl_seconds)

    forecast_points = payload.get("forecast_1h")
    forecast_1h = json.dumps(forecast_points) if forecast_points is not None else None

    return NormalizedTelemetryEvent(
        source_name=source_name,
        source_venue_id=str(source_venue_id),
        observed_at=observed_at,
        load_percent=load_percent,
        avg_wait_minutes=avg_wait_minutes,
        level=level_for_load_percent(load_percent),
        forecast_start_time=forecast_start_time,
        forecast_end_time=forecast_end_time,
        features_snapshot_id=_snapshot_id(payload),
        forecast_1h=forecast_1h,
    )


def resolve_venue_id(cursor, event: NormalizedTelemetryEvent) -> str | None:
    cursor.execute(
        "SELECT venue_id FROM venue_source_links WHERE source_name = %s AND source_record_id = %s",
        (event.source_name, event.source_venue_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return row["venue_id"]
    return row[0]


def upsert_busyness_score(cursor, venue_id: str, event: NormalizedTelemetryEvent) -> None:
    cursor.execute(
        "INSERT INTO busyness_scores "
        "(venue_id, score, level, estimated_wait_minutes, forecast_1h, "
        "forecast_start_time, forecast_end_time, model_version, features_snapshot_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "score = %s, level = %s, estimated_wait_minutes = %s, forecast_1h = %s, "
        "forecast_end_time = %s, features_snapshot_id = %s, created_at = CURRENT_TIMESTAMP",
        (
            venue_id,
            event.load_percent,
            event.level,
            event.avg_wait_minutes,
            event.forecast_1h,
            event.forecast_start_time,
            event.forecast_end_time,
            MODEL_VERSION,
            event.features_snapshot_id,
            event.load_percent,
            event.level,
            event.avg_wait_minutes,
            event.forecast_1h,
            event.forecast_end_time,
            event.features_snapshot_id,
        ),
    )


def process_batch(cursor, payloads: list[dict[str, Any]]) -> BatchIngestionResult:
    ingested = 0
    rejected = 0
    unmatched = []

    for payload in payloads:
        try:
            event = normalize_event(payload)
        except TelemetryValidationError:
            rejected += 1
            continue

        venue_id = resolve_venue_id(cursor, event)
        if not venue_id:
            unmatched.append(f"{event.source_name}:{event.source_venue_id}")
            continue

        upsert_busyness_score(cursor, venue_id, event)
        ingested += 1

    return BatchIngestionResult(
        received=len(payloads),
        ingested=ingested,
        rejected=rejected,
        unmatched=unmatched,
    )

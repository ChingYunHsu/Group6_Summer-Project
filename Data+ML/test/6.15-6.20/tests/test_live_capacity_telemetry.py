"""Tests for objective live capacity telemetry ingestion."""

from datetime import datetime, timedelta

import pytest


class FakeCursor:
    def __init__(self):
        self.source_links = {
            ("local_test_snapshot", "venue-seed-001"): "seed-restroom-bryant-park-001"
        }
        self.rows = {}
        self.unmatched = []
        self.rowcount = 0

    def execute(self, query, params=()):
        query = " ".join(query.split())

        if query.startswith("SELECT venue_id FROM venue_source_links"):
            self._result = self.source_links.get((params[0], params[1]))
        elif query.startswith("INSERT INTO busyness_scores"):
            (
                venue_id,
                score,
                level,
                wait_minutes,
                forecast_1h,
                forecast_start,
                forecast_end,
                model_version,
                snapshot_id,
                updated_score,
                updated_level,
                updated_wait,
                updated_forecast,
                updated_end,
                updated_snapshot,
            ) = params
            key = (venue_id, forecast_start, model_version)
            self.rows[key] = {
                "venue_id": venue_id,
                "score": updated_score if key in self.rows else score,
                "level": updated_level if key in self.rows else level,
                "estimated_wait_minutes": updated_wait if key in self.rows else wait_minutes,
                "forecast_1h": updated_forecast if key in self.rows else forecast_1h,
                "forecast_start_time": forecast_start,
                "forecast_end_time": updated_end if key in self.rows else forecast_end,
                "model_version": model_version,
                "features_snapshot_id": updated_snapshot if key in self.rows else snapshot_id,
            }
            self.rowcount += 1
            self._result = None
        else:
            raise AssertionError(f"unexpected SQL: {query!r}")

    def fetchone(self):
        if self._result is None:
            return None
        return {"venue_id": self._result}


def test_normalize_live_capacity_event_maps_percent_and_wait_time():
    from live_capacity_telemetry import normalize_event

    event = normalize_event(
        {
            "source_name": "local_test_snapshot",
            "source_venue_id": "venue-seed-001",
            "observed_at": "2026-06-29T12:34:45Z",
            "load_percent": 71.8,
            "avg_wait_minutes": 9.2,
            "ttl_seconds": 120,
        }
    )

    assert event.source_name == "local_test_snapshot"
    assert event.load_percent == 72
    assert event.level == "busy"
    assert event.avg_wait_minutes == 9
    assert event.forecast_start_time == datetime(2026, 6, 29, 12, 34)
    assert event.forecast_end_time == datetime(2026, 6, 29, 12, 36)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"avg_wait_minutes": 4, "observed_at": "2026-06-29T12:00:00Z"}, "source_venue_id"),
        (
            {
                "source_venue_id": "venue-seed-001",
                "observed_at": "2026-06-29T12:00:00Z",
                "load_percent": 101,
                "avg_wait_minutes": 4,
            },
            "load_percent",
        ),
        (
            {
                "source_venue_id": "venue-seed-001",
                "observed_at": "2026-06-29T12:00:00Z",
                "load_percent": 50,
                "avg_wait_minutes": -1,
            },
            "avg_wait_minutes",
        ),
    ],
)
def test_normalize_live_capacity_event_rejects_invalid_payloads(payload, message):
    from live_capacity_telemetry import TelemetryValidationError, normalize_event

    with pytest.raises(TelemetryValidationError, match=message):
        normalize_event(payload)


def test_process_batch_resolves_venues_and_upserts_busyness_rows():
    from live_capacity_telemetry import process_batch

    cursor = FakeCursor()
    observed_at = datetime(2026, 6, 29, 12, 10, 44)
    result = process_batch(
        cursor,
        [
            {
                "source_name": "local_test_snapshot",
                "source_venue_id": "venue-seed-001",
                "observed_at": observed_at.isoformat(),
                "load_percent": 33,
                "avg_wait_minutes": 5,
            },
            {
                "source_name": "local_test_snapshot",
                "source_venue_id": "missing",
                "observed_at": observed_at.isoformat(),
                "load_percent": 90,
                "avg_wait_minutes": 15,
            },
        ],
    )

    key = ("seed-restroom-bryant-park-001", datetime(2026, 6, 29, 12, 10), "live-telemetry-v1")
    assert result.ingested == 1
    assert result.unmatched == ["local_test_snapshot:missing"]
    assert cursor.rows[key]["score"] == 33
    assert cursor.rows[key]["level"] == "quiet"
    assert cursor.rows[key]["estimated_wait_minutes"] == 5
    assert cursor.rows[key]["forecast_end_time"] == datetime(2026, 6, 29, 12, 15)

    process_batch(
        cursor,
        [
            {
                "source_name": "local_test_snapshot",
                "source_venue_id": "venue-seed-001",
                "observed_at": observed_at + timedelta(seconds=5),
                "load_percent": 67,
                "avg_wait_minutes": 11,
                "features_snapshot_id": "update-1",
            }
        ],
    )

    assert len(cursor.rows) == 1
    assert cursor.rows[key]["score"] == 67
    assert cursor.rows[key]["level"] == "moderate"
    assert cursor.rows[key]["features_snapshot_id"] == "update-1"

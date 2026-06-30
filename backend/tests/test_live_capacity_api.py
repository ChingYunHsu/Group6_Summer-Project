"""Tests for DB-backed live capacity map/detail APIs."""

from datetime import datetime, timedelta

import api.realtime as realtime_module
import api.venues as venues_module


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False

    def cursor(self):
        return FakeCursor(self.rows)

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        query = " ".join(query.split())
        now = params[-1]
        if "WHERE venue_id = %s" in query:
            venue_id = params[0]
            candidates = [
                row
                for row in self.rows
                if row["venue_id"] == venue_id
                and row["forecast_start_time"] <= now
                and row["forecast_end_time"] > now
            ]
            candidates.sort(key=lambda row: row["forecast_start_time"], reverse=True)
            row = candidates[0] if candidates else None
            self._result = (
                (
                    row["score"],
                    row["level"],
                    row["estimated_wait_minutes"],
                    row["created_at"],
                    row["forecast_end_time"],
                )
                if row
                else None
            )
        elif "WHERE model_version = %s" in query:
            since = params[1]
            self._result = [
                (
                    row["venue_id"],
                    row["score"],
                    row["level"],
                    row["estimated_wait_minutes"],
                    row["created_at"],
                    row["forecast_end_time"],
                )
                for row in self.rows
                if row["model_version"] == params[0] and row["created_at"] >= since
            ]
        else:
            raise AssertionError(f"unexpected SQL: {query!r}")

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result


def test_venue_busyness_returns_live_db_wait_and_expiry(client, monkeypatch):
    now = datetime.now()
    rows = [
        {
            "venue_id": "v_live",
            "score": 82,
            "level": "busy",
            "estimated_wait_minutes": 18,
            "forecast_start_time": now - timedelta(minutes=1),
            "forecast_end_time": now + timedelta(minutes=4),
            "created_at": now,
            "model_version": "live-telemetry-v1",
        }
    ]
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: FakeConnection(rows))

    resp = client.get("/api/v1/venues/v_live/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()["busyness"]
    assert data["data_mode"] == "live"
    assert data["busyness_score"] == 82
    assert data["busyness_status"] == "busy"
    assert data["estimated_wait_minutes"] == 18
    assert data["expires_at"].endswith("Z")


def test_venue_busyness_ignores_expired_live_rows(client, monkeypatch):
    now = datetime.now()
    rows = [
        {
            "venue_id": "v_expired",
            "score": 95,
            "level": "busy",
            "estimated_wait_minutes": 40,
            "forecast_start_time": now - timedelta(minutes=10),
            "forecast_end_time": now - timedelta(minutes=5),
            "created_at": now - timedelta(minutes=10),
            "model_version": "live-telemetry-v1",
        }
    ]
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: FakeConnection(rows))

    resp = client.get("/api/v1/venues/v_expired/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 404


def test_realtime_map_updates_streams_recent_db_rows(client, monkeypatch):
    now = datetime.now()
    rows = [
        {
            "venue_id": "v_live",
            "score": 45,
            "level": "moderate",
            "estimated_wait_minutes": 7,
            "forecast_start_time": now - timedelta(minutes=1),
            "forecast_end_time": now + timedelta(minutes=4),
            "created_at": now,
            "model_version": "live-telemetry-v1",
        }
    ]
    monkeypatch.setattr(realtime_module, "_get_db_conn", lambda: FakeConnection(rows))

    resp = client.get("/api/v1/realtime/map-updates", headers={"X-API-Key": "dev-api-key"})
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    assert "event: venue_update" in body
    assert '"venue_id": "v_live"' in body
    assert '"busyness_score": 45' in body
    assert '"estimated_wait_minutes": 7' in body
    assert '"expires_at":' in body

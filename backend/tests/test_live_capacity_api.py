"""Tests for DB-backed live capacity map/detail APIs."""

from datetime import datetime, timedelta, timezone

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


class _ForecastConnection:
    """Fake connection whose cursor serves busyness_forecasts rows.

    Returns the same row set for every execute() call (the forecast endpoint
    issues a single query against busyness_forecasts), filtering to rows whose
    `forecast_for` is >= the query's NOW() param."""

    def __init__(self, rows):
        self.rows = rows
        self.closed = False

    def cursor(self):
        return _ForecastCursor(self.rows)

    def close(self):
        self.closed = True


class _ForecastCursor:
    def __init__(self, rows):
        self.rows = rows
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        # The forecast query passes only (venue_id,); NOW() is evaluated
        # server-side. Fake it with the test's notion of "now".
        venue_id = params[0]
        now = datetime.now(timezone.utc)
        self._result = [
            (
                row["forecast_for"],
                row["predicted_score"],
                row["predicted_level"],
                row["estimated_wait_minutes"],
                row["model_version"],
                row.get("generated_at", row["forecast_for"]),
            )
            for row in self.rows
            if row["venue_id"] == venue_id and row["forecast_for"] >= now
        ]

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result

    def close(self):
        pass



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


# ---------------------------------------------------------------------------
# SOP 3 — /venues/{id}/busyness/forecast backed by busyness_forecasts table
# ---------------------------------------------------------------------------

def _forecast_rows(venue_id, scores):
    """Build busyness_forecasts row dicts at +1h, +2h, ... from now."""
    now = datetime.now(timezone.utc)
    rows = []
    for i, score in enumerate(scores, start=1):
        rows.append({
            "venue_id": venue_id,
            "forecast_for": now + timedelta(hours=i),
            "predicted_score": score,
            "predicted_level": "busy" if score > 70 else ("moderate" if score >= 30 else "quiet"),
            "estimated_wait_minutes": score // 4,
            "model_version": "ridge-v1",
        })
    return rows


def test_forecast_returns_12h_series_from_db(client, monkeypatch):
    rows = _forecast_rows("v_fc", [80, 75, 70, 60, 50, 40, 30, 25, 20, 35, 55, 65])
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _ForecastConnection(rows))

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "forecast"
    assert data["forecast_source"] == "busyness_forecasts"
    assert len(data["forecast"]) == 12
    assert data["forecast"][0]["percent"] == 80
    assert data["forecast"][0]["level"] in {"quiet", "moderate", "busy"}
    assert "forecast_for" in data["forecast"][0]
    assert data["forecast"][0]["estimated_wait_minutes"] == 20
    # best_time picks the lowest predicted_score (20, at offset 9h)
    assert data["best_time_to_go_today"]["percent"] == 20
    assert data["best_time_to_go_today"]["offset_hours"] == 9
    assert data["best_time_to_go_today"]["label"] == "In 9 hours"


def test_forecast_handles_fewer_than_12_rows(client, monkeypatch):
    rows = _forecast_rows("v_fc", [60, 45, 30])
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _ForecastConnection(rows))

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "forecast"
    assert len(data["forecast"]) == 3
    assert data["best_time_to_go_today"]["percent"] == 30


def test_forecast_falls_back_to_mock_when_no_db_rows(client, monkeypatch):
    # Empty busyness_forecasts AND no forecast_1h → connection returns no rows,
    # then the forecast_1h path also returns nothing → mock fallback for v_1001.
    class _EmptyConn:
        def __init__(self, rows):
            self.rows = rows

        def cursor(self):
            return _ForecastCursor(self.rows)

        def close(self):
            pass

    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _EmptyConn([]))

    resp = client.get("/api/v1/venues/v_1001/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "mock"
    assert data["forecast_source"] == "mock_data"
    assert len(data["forecast"]) == 12  # VENUE_FORECASTS["v_1001"] has 12h mock


def test_forecast_tie_break_on_lowest_score_is_stable(client, monkeypatch):
    # Two equal-lowest scores (25) — best_time must pick one with a valid label.
    rows = _forecast_rows("v_fc", [25, 90, 25, 90])
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _ForecastConnection(rows))

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["best_time_to_go_today"]["percent"] == 25
    assert data["best_time_to_go_today"]["label"].startswith("In ")


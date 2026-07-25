"""Tests for DB-backed live capacity map/detail APIs.

Sprint 5 SOP: both /venues/{id}/busyness and /venues/{id}/busyness/forecast
are V2-only now — clinic/hospital/pharmacy with a current forecast-v2 row,
or the unavailable payload. No live-telemetry, traffic-baseline, legacy
forecast_1h, or mock fallback is client-visible from either endpoint.
"""

from datetime import datetime, timedelta, timezone

import api.realtime as realtime_module
import api.venues as venues_module


class FakeConnection:
    """Fake for api.realtime's busyness_scores queries — untouched by the
    Sprint 5 V2-only rule, which only applies to the two venues.py busyness
    endpoints."""

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
        if "WHERE model_version = %s" in query:
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
# Sprint 5 SOP — V2-only /venues/{id}/busyness and .../busyness/forecast
# ---------------------------------------------------------------------------

class _V2Connection:
    """Fake connection serving the two query shapes both busyness endpoints
    now issue: a venue_type lookup against `venues`, then a forecast-v2 row
    (or 12-row series) against `busyness_forecasts` restricted to each
    venue's latest batch and future forecast_for timestamps."""

    def __init__(self, venue_types: dict, forecasts: dict):
        self.venue_types = venue_types
        self.forecasts = forecasts

    def cursor(self):
        return _V2Cursor(self.venue_types, self.forecasts)

    def close(self):
        pass


class _V2Cursor:
    def __init__(self, venue_types, forecasts):
        self.venue_types = venue_types
        self.forecasts = forecasts
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        query = " ".join(query.split())
        now = datetime.now(timezone.utc)

        if "SELECT venue_type FROM venues" in query:
            venue_id = params[0]
            venue_type = self.venue_types.get(venue_id)
            self._result = (venue_type,) if venue_type is not None else None
            return

        if "FROM busyness_forecasts" in query:
            venue_id = params[0]
            # The two callers SELECT different column orders/widths — the
            # forecast endpoint includes model_version, the busyness
            # endpoint doesn't and puts forecast_for last.
            is_forecast_series_query = "model_version, generated_at" in query
            matching = [
                row for row in self.forecasts.get(venue_id, [])
                if row.get("model_version", "forecast-v2") == "forecast-v2"
                and row["forecast_for"] >= now
            ]
            matching.sort(key=lambda r: r["forecast_for"])

            if is_forecast_series_query:
                rows = [
                    (
                        row["forecast_for"],
                        row["predicted_score"],
                        row["predicted_level"],
                        row["estimated_wait_minutes"],
                        row.get("model_version", "forecast-v2"),
                        row.get("generated_at", now),
                    )
                    for row in matching
                ]
                self._result = rows[:12]
            else:
                rows = [
                    (
                        row["predicted_score"],
                        row["predicted_level"],
                        row["estimated_wait_minutes"],
                        row["forecast_for"],
                        row.get("generated_at", now),
                    )
                    for row in matching
                ]
                self._result = rows[:1]
            return

        raise AssertionError(f"unexpected SQL: {query!r}")

    def fetchone(self):
        if isinstance(self._result, list):
            return self._result[0] if self._result else None
        return self._result

    def fetchall(self):
        return self._result if isinstance(self._result, list) else []

    def close(self):
        pass


def _forecast_rows(scores, start_hours=1):
    now = datetime.now(timezone.utc)
    return [
        {
            "forecast_for": now + timedelta(hours=start_hours + i),
            "predicted_score": score,
            "predicted_level": "busy" if score > 70 else ("moderate" if score >= 30 else "quiet"),
            "estimated_wait_minutes": score // 4,
        }
        for i, score in enumerate(scores)
    ]


# --- GET /venues/{id}/busyness ---

def test_busyness_eligible_venue_with_v2_data_returns_forecast(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v1": "clinic"}, {"v1": _forecast_rows([42])}),
    )

    resp = client.get("/api/v1/venues/v1/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()["busyness"]
    assert data["data_mode"] == "forecast"
    assert data["forecast_source"] == "busyness_forecasts"
    assert data["busyness_score"] == 42
    assert "unavailable_reason" not in data


def test_busyness_aed_always_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v_aed": "emergencyasset"}, {"v_aed": _forecast_rows([10])}),
    )

    resp = client.get("/api/v1/venues/v_aed/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()["busyness"]
    assert data["data_mode"] == "unavailable"
    assert data["unavailable_reason"] == "no_v2_forecast"
    assert data["busyness_status"] == "no_data"


def test_busyness_restroom_always_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v_wc": "restroom"}, {}),
    )

    resp = client.get("/api/v1/venues/v_wc/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    assert resp.get_json()["busyness"]["data_mode"] == "unavailable"


def test_busyness_eligible_venue_without_v2_rows_is_unavailable_not_404(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v1": "hospital"}, {}),
    )

    resp = client.get("/api/v1/venues/v1/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    assert resp.get_json()["busyness"]["data_mode"] == "unavailable"


def test_busyness_expired_v2_rows_only_is_unavailable(client, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection(
            {"v1": "pharmacy"},
            {"v1": [{
                "forecast_for": now - timedelta(hours=2),
                "predicted_score": 90,
                "predicted_level": "busy",
                "estimated_wait_minutes": 20,
            }]},
        ),
    )

    resp = client.get("/api/v1/venues/v1/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    assert resp.get_json()["busyness"]["data_mode"] == "unavailable"


def test_busyness_unknown_venue_returns_404(client, monkeypatch):
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _V2Connection({}, {}))

    resp = client.get("/api/v1/venues/v_ghost/busyness", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 404


# --- GET /venues/{id}/busyness/forecast ---

def test_forecast_returns_12h_series_for_eligible_venue(client, monkeypatch):
    scores = [80, 75, 70, 60, 50, 40, 30, 25, 20, 35, 55, 65]
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v_fc": "clinic"}, {"v_fc": _forecast_rows(scores)}),
    )

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "forecast"
    assert data["forecast_source"] == "busyness_forecasts"
    assert len(data["forecast"]) == 12
    assert data["forecast"][0]["percent"] == 80
    assert data["best_time_to_go_today"]["percent"] == 20
    assert data["best_time_to_go_today"]["offset_hours"] == 9


def test_forecast_handles_fewer_than_12_rows(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v_fc": "hospital"}, {"v_fc": _forecast_rows([60, 45, 30])}),
    )

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["forecast"]) == 3
    assert data["best_time_to_go_today"]["percent"] == 30


def test_forecast_tie_break_on_lowest_score_is_stable(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v_fc": "pharmacy"}, {"v_fc": _forecast_rows([25, 90, 25, 90])}),
    )

    resp = client.get("/api/v1/venues/v_fc/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["best_time_to_go_today"]["percent"] == 25
    assert data["best_time_to_go_today"]["label"].startswith("In ")


def test_forecast_aed_and_restroom_are_unavailable_with_empty_forecast(client, monkeypatch):
    for venue_type in ("emergencyasset", "restroom"):
        monkeypatch.setattr(
            venues_module, "_get_db_conn",
            lambda vt=venue_type: _V2Connection({"v1": vt}, {"v1": _forecast_rows([10, 20])}),
        )

        resp = client.get("/api/v1/venues/v1/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data_mode"] == "unavailable"
        assert data["unavailable_reason"] == "no_v2_forecast"
        assert data["forecast"] == []


def test_forecast_eligible_venue_without_v2_rows_is_unavailable_not_404(client, monkeypatch):
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection({"v1": "clinic"}, {}),
    )

    resp = client.get("/api/v1/venues/v1/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    assert resp.get_json()["data_mode"] == "unavailable"


def test_forecast_expired_v2_rows_are_excluded_not_returned_as_current(client, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        venues_module, "_get_db_conn",
        lambda: _V2Connection(
            {"v1": "clinic"},
            {"v1": [{
                "forecast_for": now - timedelta(hours=1),
                "predicted_score": 99,
                "predicted_level": "busy",
                "estimated_wait_minutes": 30,
            }]},
        ),
    )

    resp = client.get("/api/v1/venues/v1/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data_mode"] == "unavailable"
    assert data["forecast"] == []


def test_forecast_unknown_venue_returns_404(client, monkeypatch):
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _V2Connection({}, {}))

    resp = client.get("/api/v1/venues/v_ghost/busyness/forecast", headers={"X-API-Key": "dev-api-key"})

    assert resp.status_code == 404

"""Unit tests for the forecast endpoint's 5-minute response cache."""

import api.venues as venues_module


class _CountingCursor:
    """Records how many times execute() is called against busyness_forecasts."""

    calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        _CountingCursor.calls += 1

    def fetchall(self):
        return [
            (
                __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                + __import__("datetime").timedelta(hours=1),
                42,
                "moderate",
                10,
                "forecast-v2",
                None,
            )
        ]

    def fetchone(self):
        return None


class _CountingConn:
    def cursor(self):
        return _CountingCursor()

    def close(self):
        pass


def test_forecast_endpoint_serves_second_request_from_cache(client, monkeypatch):
    _CountingCursor.calls = 0
    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _CountingConn())

    first = client.get("/api/v1/venues/v_cache_test/busyness/forecast", headers={"X-API-Key": "test"})
    second = client.get("/api/v1/venues/v_cache_test/busyness/forecast", headers={"X-API-Key": "test"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json() == second.get_json()

    calls_after_first = _CountingCursor.calls
    assert calls_after_first > 0  # the (uncached) first request hit the DB

    client.get("/api/v1/venues/v_cache_test/busyness/forecast", headers={"X-API-Key": "test"})
    # A third request for the same venue must still be served from cache —
    # no additional DB calls beyond what the first request already made.
    assert _CountingCursor.calls == calls_after_first


def test_forecast_cache_uses_5_minute_ttl(monkeypatch):
    captured = {}

    def fake_set(key, value, ttl_seconds):
        captured["ttl"] = ttl_seconds

    monkeypatch.setattr(venues_module, "set_cached", fake_set)
    monkeypatch.setattr(venues_module, "get_cached", lambda key: None)
    monkeypatch.setattr(
        venues_module,
        "_compute_venue_busyness_forecast",
        lambda venue_id: {"venue_id": venue_id, "forecast": []},
    )

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        client.get("/api/v1/venues/v_ttl_test/busyness/forecast", headers={"X-API-Key": "test"})

    assert captured["ttl"] == 300


def test_forecast_cache_is_isolated_per_venue(client, monkeypatch):
    class _Cur:
        def __init__(self, score):
            self.score = score

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=()):
            pass

        def fetchall(self):
            import datetime as dt

            return [
                (
                    dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
                    self.score,
                    "moderate",
                    5,
                    "forecast-v2",
                    None,
                )
            ]

        def fetchone(self):
            return None

    class _Conn:
        def __init__(self, score):
            self.score = score

        def cursor(self):
            return _Cur(self.score)

        def close(self):
            pass

    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _Conn(11))
    resp_a = client.get("/api/v1/venues/v_a/busyness/forecast", headers={"X-API-Key": "test"})

    monkeypatch.setattr(venues_module, "_get_db_conn", lambda: _Conn(99))
    resp_b = client.get("/api/v1/venues/v_b/busyness/forecast", headers={"X-API-Key": "test"})

    assert resp_a.get_json()["forecast"][0]["percent"] == 11
    assert resp_b.get_json()["forecast"][0]["percent"] == 99

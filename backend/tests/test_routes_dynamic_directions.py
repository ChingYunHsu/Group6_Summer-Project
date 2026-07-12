"""Unit tests for the now-dynamic /routes/options and /routes/detail,
with the DB and Google Maps client faked out."""

from contextlib import contextmanager

import api.routes as routes_module


class _FakeCursor:
    def __init__(self, venue):
        self._venue = venue

    def execute(self, query, params=()):
        self._matched = self._venue if params[0] == self._venue["venue_id"] else None

    def fetchone(self):
        return self._matched


VENUE = {"venue_id": "v_1002", "latitude": 40.7061, "longitude": -73.9969}


def _directions_response(duration_seconds, polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@", steps=None):
    return {
        "status": "OK",
        "routes": [
            {
                "overview_polyline": {"points": polyline},
                "legs": [
                    {
                        "duration": {"value": duration_seconds},
                        "steps": steps
                        or [
                            {"html_instructions": "Walk <b>north</b> on 5th Ave"},
                            {"html_instructions": "Turn <b>left</b> onto 42nd St"},
                        ],
                    }
                ],
            }
        ],
    }


def test_route_options_falls_back_to_mock_without_params(client):
    resp = client.get("/api/v1/routes/options", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    assert resp.get_json()["destination_venue_id"] == "v_1002"  # from ROUTE_OPTIONS mock


def test_route_options_uses_live_directions_when_params_given(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(VENUE)

    monkeypatch.setattr(routes_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(
        routes_module.google_maps_client,
        "get_directions",
        lambda origin, destination, mode: _directions_response(
            {"walking": 900, "transit": 600, "driving": 480}[mode]
        ),
    )

    resp = client.get(
        "/api/v1/routes/options?destination_venue_id=v_1002&origin_lat=40.75&origin_lon=-73.98",
        headers={"X-API-Key": "test"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["summary_by_mode"]["walk"]["duration_minutes"] == 15
    assert body["summary_by_mode"]["transit"]["duration_minutes"] == 10
    assert body["summary_by_mode"]["drive"]["duration_minutes"] == 8
    # options sorted ascending by duration
    assert [option["mode"] for option in body["options"]] == ["drive", "transit", "walk"]


def test_route_options_falls_back_to_mock_on_unknown_venue(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(VENUE)

    monkeypatch.setattr(routes_module, "db_cursor", fake_db_cursor)

    resp = client.get(
        "/api/v1/routes/options?destination_venue_id=v_does_not_exist&origin_lat=40.75&origin_lon=-73.98",
        headers={"X-API-Key": "test"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["destination_venue_id"] == "v_1002"  # mock fallback


def test_route_detail_falls_back_to_mock_without_params(client):
    resp = client.get("/api/v1/routes/detail", headers={"X-API-Key": "test"})
    assert resp.status_code == 200
    assert resp.get_json()["destination_venue_id"] == "v_1002"


def test_route_detail_uses_live_directions_and_decodes_polyline(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(VENUE)

    monkeypatch.setattr(routes_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(
        routes_module.google_maps_client,
        "get_directions",
        lambda origin, destination, mode: _directions_response(600),
    )
    monkeypatch.setattr(
        routes_module.google_maps_client,
        "decode_polyline",
        lambda points: [{"latitude": 38.5, "longitude": -120.2}],
    )

    resp = client.get(
        "/api/v1/routes/detail?destination_venue_id=v_1002&origin_lat=40.75&origin_lon=-73.98&mode=transit",
        headers={"X-API-Key": "test"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["polyline_preview"] == [{"latitude": 38.5, "longitude": -120.2}]
    # HTML tags stripped from step instructions
    assert body["steps"] == ["Walk north on 5th Ave", "Turn left onto 42nd St"]


def test_route_detail_falls_back_to_mock_on_maps_api_failure(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(VENUE)

    monkeypatch.setattr(routes_module, "db_cursor", fake_db_cursor)

    def _raise(*args, **kwargs):
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    monkeypatch.setattr(routes_module.google_maps_client, "get_directions", _raise)

    resp = client.get(
        "/api/v1/routes/detail?destination_venue_id=v_1002&origin_lat=40.75&origin_lon=-73.98",
        headers={"X-API-Key": "test"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["destination_venue_id"] == "v_1002"  # mock fallback shape
    assert "steps" in resp.get_json()

"""Unit tests for the Google Maps Directions REST client."""

import pytest

import google_maps_client


def test_decode_polyline_matches_googles_documented_example():
    # https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    result = google_maps_client.decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")

    expected = [
        {"latitude": 38.5, "longitude": -120.2},
        {"latitude": 40.7, "longitude": -120.95},
        {"latitude": 43.252, "longitude": -126.453},
    ]
    assert len(result) == len(expected)
    for actual, exp in zip(result, expected):
        assert actual["latitude"] == pytest.approx(exp["latitude"], abs=1e-4)
        assert actual["longitude"] == pytest.approx(exp["longitude"], abs=1e-4)


def test_decode_polyline_empty_string_returns_empty_list():
    assert google_maps_client.decode_polyline("") == []


def test_get_directions_requires_api_key(app):
    with app.app_context():
        app.config["GOOGLE_MAPS_API_KEY"] = ""
        try:
            google_maps_client.get_directions((40.0, -73.0), (40.1, -73.1), "walking")
            assert False, "should have raised"
        except RuntimeError as exc:
            assert "GOOGLE_MAPS_API_KEY" in str(exc)

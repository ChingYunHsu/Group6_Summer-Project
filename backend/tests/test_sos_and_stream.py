"""Unit tests for the SOS webhook buffer and the persistent SSE stream that
drains it. No live DB/Redis required."""

import api.realtime as realtime_module
import sos_buffer


def test_sos_endpoint_buffers_event_and_returns_incident_id(client):
    resp = client.post(
        "/api/v1/user/sos",
        json={"latitude": 40.74, "longitude": -73.98, "tracking_metrics": {"speed_kmh": 3.1}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "accepted"
    assert body["incident_id"].startswith("sos_")

    buffered = sos_buffer.drain_sos_events()
    assert len(buffered) == 1
    assert buffered[0]["incident_id"] == body["incident_id"]
    assert buffered[0]["tracking_metrics"] == {"speed_kmh": 3.1}


def test_sos_endpoint_rejects_unknown_fields(client):
    resp = client.post("/api/v1/user/sos", json={"unexpected_field": "x"})
    assert resp.status_code == 400


def test_stream_yields_sos_event_then_heartbeat():
    sos_buffer.push_sos_event({"incident_id": "sos_test", "latitude": 1.0, "longitude": 2.0})

    chunks = list(realtime_module.generate_live_stream(max_iterations=1))

    assert any(chunk.startswith("event: sos_telemetry") and "sos_test" in chunk for chunk in chunks)
    assert chunks[-1] == ": heartbeat\n\n"


def test_stream_response_has_event_stream_headers(client):
    resp = client.get(
        "/api/v1/realtime/map-updates",
        headers={"X-API-Key": "test"},
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"

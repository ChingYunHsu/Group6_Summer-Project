"""Unit tests for the report submission wizard's Path A (venue-bound) /
Path B (GPS standalone) branching. DB persistence is best-effort in
api/reports.py, so these run fine without a live MySQL/Redis."""

import mock_data


def _drop_report(report_id: str) -> None:
    mock_data.REPORTS[:] = [r for r in mock_data.REPORTS if r["report_id"] != report_id]


def test_path_a_venue_bound_report_accepted(client):
    resp = client.post(
        "/api/v1/reports",
        json={"issue_type": "large_crowd", "venue_id": "venue_a"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["report_path"] == "venue_bound"
    _drop_report(resp.get_json()["report_id"])


def test_path_b_gps_standalone_report_accepted(client):
    resp = client.post(
        "/api/v1/reports",
        json={"issue_type": "elevator_broken", "latitude": 40.74, "longitude": -73.98},
    )
    assert resp.status_code == 201
    assert resp.get_json()["report_path"] == "gps_standalone"
    _drop_report(resp.get_json()["report_id"])


def test_report_missing_both_venue_and_coordinates_rejected(client):
    resp = client.post("/api/v1/reports", json={"issue_type": "large_crowd"})
    assert resp.status_code == 400
    assert "missing_fields" in resp.get_json()


def test_report_missing_issue_type_rejected(client):
    resp = client.post("/api/v1/reports", json={"venue_id": "venue_a"})
    assert resp.status_code == 400


def test_still_here_confirmation_bumps_count(client, monkeypatch):
    submit = client.post(
        "/api/v1/reports",
        json={"issue_type": "large_crowd", "venue_id": "venue_a"},
    )
    report_id = submit.get_json()["report_id"]

    resp = client.post(f"/api/v1/reports/{report_id}/confirmations", json={"action": "still_here"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "confirmed"
    assert body["report"]["confirmation_count"] == 1

    _drop_report(report_id)

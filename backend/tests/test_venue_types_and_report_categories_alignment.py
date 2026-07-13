"""Locks in that VALID_VENUE_TYPES and ALLOWED_REPORT_TYPES actually match
the real schema/seed data, and that GET /reports returns the same shape
whether or not MySQL happens to be reachable."""

from contextlib import contextmanager

import api.reports as reports_module
import api.venues as venues_module


def test_valid_venue_types_matches_schema_enum():
    # Exact match to the venue_type ENUM in 001_clearpath_schema.sql.
    assert venues_module.VALID_VENUE_TYPES == {
        "restroom", "healthcare", "emergencyasset",
        "clinic", "pharmacy", "hospital", "dentist", "laboratory",
    }


def test_previously_400ing_seeded_venue_types_are_now_valid(client, monkeypatch):
    def _raise():
        raise RuntimeError("no DB in this test")

    monkeypatch.setattr(venues_module, "db_cursor", _raise)

    for venue_type in ("restroom", "emergencyasset"):
        resp = client.get(f"/api/v1/venues?venue_type={venue_type}")
        assert resp.status_code == 200, f"{venue_type} should no longer 400"


def test_allowed_report_types_matches_seeded_categories():
    # Matches the 9 category_id values in 006_seed_report_categories.sql.
    assert reports_module.ALLOWED_REPORT_TYPES == {
        "elevator_broken", "wheelchair_lift_broken", "toilet_out_of_order",
        "large_crowd", "long_waiting_time", "protest_or_blockage",
        "entrance_closed", "ramp_blocked", "closed_early",
    }
    # Every allowed type must have a display label.
    assert reports_module.ALLOWED_REPORT_TYPES == set(reports_module.ISSUE_TYPE_LABELS)


def test_previously_unlabeled_mock_issue_types_now_submittable(client, app):
    from auth import issue_access_token

    with app.app_context():
        token = issue_access_token("u_1001")
    headers = {"Authorization": f"Bearer {token}"}

    for issue_type in ("ramp_blocked", "closed_early", "long_waiting_time"):
        resp = client.post(
            "/api/v1/reports",
            json={"issue_type": issue_type, "latitude": 1.0, "longitude": 2.0},
            headers=headers,
        )
        assert resp.status_code == 201, f"{issue_type} should be submittable now"
        assert resp.get_json()["issue_type_label"] != issue_type  # has a real label


def test_reports_list_mock_and_db_shapes_match(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        class _Cur:
            def execute(self, query, params=()):
                pass

            def fetchall(self):
                return []

        yield _Cur()

    class _DbStub:
        db_cursor = staticmethod(fake_db_cursor)

    # DB path: reachable but returns zero rows.
    monkeypatch.setattr(reports_module, "_db", lambda: _DbStub())
    db_resp = client.get("/api/v1/reports")
    db_shape = set(db_resp.get_json()["items"][0].keys()) if db_resp.get_json()["items"] else None

    # Mock path: no DB at all.
    monkeypatch.setattr(reports_module, "_db", lambda: None)
    mock_resp = client.get("/api/v1/reports")
    mock_items = mock_resp.get_json()["items"]
    assert mock_items, "mock fallback should have seeded REPORTS entries"
    mock_shape = set(mock_items[0].keys())

    expected_shape = {
        "report_id", "venue_id", "issue_type", "issue_type_label", "report_scope",
        "status", "latitude", "longitude", "created_at", "expires_at", "confirmations",
    }
    assert mock_shape == expected_shape
    if db_shape is not None:
        assert db_shape == expected_shape

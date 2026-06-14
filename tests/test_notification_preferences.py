import pytest

URL = "/api/v1/user/notification-preferences"


@pytest.mark.parametrize(
    "payload",
    [
        {"unknown_field": True},
        {"busyness_alerts_enabled": True, "extra_garbage": "nope"},
        {"alert_threshold_percent": 50, "preferred_venue_types": ["bar"], "is_admin": True},
        {"": "blank-key"},
    ],
)
def test_update_notification_preferences_rejects_unknown_fields(client, payload):
    resp = client.put(URL, json=payload)

    assert resp.status_code == 400

    data = resp.get_json()
    assert data["error"] == "Validation failed."
    assert data["missing_fields"] == []
    assert set(data["invalid_fields"]) == {k for k in payload if k not in {
        "busyness_alerts_enabled",
        "push_notifications_enabled",
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "alert_threshold_percent",
        "preferred_venue_types",
        "preferred_boroughs",
    }}


def test_update_notification_preferences_accepts_valid_fields(client):
    resp = client.put(
        URL,
        json={"busyness_alerts_enabled": False, "alert_threshold_percent": 75},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["busyness_alerts_enabled"] is False
    assert data["alert_threshold_percent"] == 75

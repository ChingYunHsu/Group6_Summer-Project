"""Locks in the PRD Web Read-Only constraint (documented in openapi.yaml
as x-web-readonly) for the two report write endpoints — this was
documented but not actually implemented until now (api/reports.py never
called web_readonly_blocked(), unlike the equivalent favourites gating
in api/user.py)."""

from auth import issue_access_token


def _token(app, user_id="u_1001"):
    with app.app_context():
        return issue_access_token(user_id)


def test_submit_report_rejects_web_client(client, app):
    headers = {
        "Authorization": f"Bearer {_token(app)}",
        "X-Client-Origin": "web",
    }
    resp = client.post(
        "/api/v1/reports",
        json={"issue_type": "large_crowd", "latitude": 1.0, "longitude": 2.0},
        headers=headers,
    )
    assert resp.status_code == 403


def test_submit_report_allows_mobile_client(client, app):
    headers = {
        "Authorization": f"Bearer {_token(app)}",
        "X-Client-Origin": "mobile",
    }
    resp = client.post(
        "/api/v1/reports",
        json={"issue_type": "large_crowd", "latitude": 1.0, "longitude": 2.0},
        headers=headers,
    )
    assert resp.status_code == 201


def test_confirm_report_rejects_web_client(client, app):
    headers = {
        "Authorization": f"Bearer {_token(app)}",
        "X-Client-Origin": "web",
    }
    resp = client.post("/api/v1/reports/r_501/confirmations", json={"action": "still_here"}, headers=headers)
    assert resp.status_code == 403

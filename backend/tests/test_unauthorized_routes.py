"""Any request hitting an auth-gated route without valid credentials must
get back a structured JSON error body, never a bare 401/403 or an
unhandled exception/HTML error page."""

import pytest


BEARER_PROTECTED_ROUTES = [
    ("get", "/api/v1/user/profile"),
    ("get", "/api/v1/user/medical-id"),
    ("get", "/api/v1/user/emergency-contacts"),
]


@pytest.mark.parametrize("method,path", BEARER_PROTECTED_ROUTES)
def test_unauthorized_bearer_route_returns_structured_error(client, method, path):
    resp = getattr(client, method)(path)

    assert resp.status_code == 401
    assert resp.is_json
    body = resp.get_json()
    assert "error" in body
    assert isinstance(body["error"], str) and body["error"]


def test_api_key_protected_route_rejects_wrong_key(client, app):
    app.config["API_KEY"] = "expected-key"

    resp = client.get("/api/v1/venues", headers={"X-API-Key": "wrong-key"})

    assert resp.status_code == 401
    body = resp.get_json()
    assert body["error"] == "Unauthorized. Invalid API key."

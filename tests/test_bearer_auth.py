import jwt
import pytest

from auth import issue_access_token

BEARER_ROUTES = [
    ("get", "/api/v1/user/profile"),
    ("get", "/api/v1/user/settings"),
    ("get", "/api/v1/user/medical-id"),
    ("put", "/api/v1/user/medical-id"),
    ("get", "/api/v1/user/emergency-contacts"),
]


@pytest.mark.parametrize("method,path", BEARER_ROUTES)
def test_bearer_routes_reject_missing_token(client, method, path):
    resp = getattr(client, method)(path, json={})

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized. Bearer token required."


@pytest.mark.parametrize("method,path", BEARER_ROUTES)
def test_bearer_routes_reject_invalid_token(client, method, path):
    resp = getattr(client, method)(
        path, json={}, headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized. Invalid token."


def test_bearer_routes_reject_expired_token(client, app):
    with app.app_context():
        expired = jwt.encode(
            {"sub": "u_1001", "exp": 0}, app.config["JWT_SECRET"], algorithm="HS256"
        )

    resp = client.get(
        "/api/v1/user/profile", headers={"Authorization": f"Bearer {expired}"}
    )

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized. Token expired."


def test_bearer_routes_accept_valid_token(client, app):
    with app.app_context():
        token = issue_access_token("u_1001")

    resp = client.get(
        "/api/v1/user/medical-id", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.get_json()["blood_type"] == "O+"


def test_api_key_routes_unaffected_by_bearer_auth(client):
    resp = client.get("/api/v1/user/favourites")

    assert resp.status_code == 200

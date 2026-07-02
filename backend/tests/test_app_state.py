import uuid

import pytest


def test_app_state_without_token_returns_guest_defaults(client):
    resp = client.get("/api/v1/app-state")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_guest"] is True
    assert data["is_authenticated"] is False


def test_app_state_with_guest_token(client):
    guest = client.post("/api/v1/auth/guest").get_json()

    resp = client.get(
        "/api/v1/app-state",
        headers={"Authorization": f"Bearer {guest['access_token']}"},
    )

    data = resp.get_json()
    assert data["is_guest"] is True
    assert data["is_authenticated"] is False


@pytest.mark.integration
def test_app_state_with_logged_in_user_token(client):
    email = f"{uuid.uuid4()}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test User", "email": email, "password": "Password123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123"},
    ).get_json()

    resp = client.get(
        "/api/v1/app-state",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )

    data = resp.get_json()
    assert data["is_guest"] is False
    assert data["is_authenticated"] is True


def test_app_state_with_unknown_token_falls_back_to_guest(client):
    resp = client.get(
        "/api/v1/app-state",
        headers={"Authorization": "Bearer not_a_real_token"},
    )

    data = resp.get_json()
    assert data["is_guest"] is True
    assert data["is_authenticated"] is False


@pytest.mark.integration
def test_app_state_with_registered_user_token(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"full_name": "New User", "email": f"{uuid.uuid4()}@example.com", "password": "Password123"},
    ).get_json()

    resp = client.get(
        "/api/v1/app-state",
        headers={"Authorization": f"Bearer {register['access_token']}"},
    )

    data = resp.get_json()
    assert data["is_guest"] is False
    assert data["is_authenticated"] is True

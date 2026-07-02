import uuid

import pytest

LOGIN_URL = "/api/v1/auth/login"
REGISTER_URL = "/api/v1/auth/register"


@pytest.mark.integration
def test_login_with_valid_credentials_returns_usable_token(client):
    email = f"{uuid.uuid4()}@example.com"
    client.post(REGISTER_URL, json={"full_name": "Test User", "email": email, "password": "Password123"})

    resp = client.post(LOGIN_URL, json={"email": email, "password": "Password123"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600

    protected = client.get(
        "/api/v1/user/medical-id", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert protected.status_code == 200


@pytest.mark.integration
def test_login_with_wrong_password_rejected(client):
    email = f"{uuid.uuid4()}@example.com"
    client.post(REGISTER_URL, json={"full_name": "Test User", "email": email, "password": "Password123"})

    resp = client.post(LOGIN_URL, json={"email": email, "password": "wrong-password"})

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized. Invalid email or password."


@pytest.mark.integration
def test_login_with_unknown_email_rejected(client):
    resp = client.post(LOGIN_URL, json={"email": f"{uuid.uuid4()}@example.com", "password": "Password123"})

    assert resp.status_code == 401


def test_login_missing_fields_returns_validation_error(client):
    resp = client.post(LOGIN_URL, json={"email": "amelia.rivera@example.com"})

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "Validation failed."
    assert data["missing_fields"] == ["password"]

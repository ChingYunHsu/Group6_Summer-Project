import uuid

import pytest

URL = "/api/v1/auth/register"


def test_register_missing_fields_returns_validation_error(client):
    resp = client.post(URL, json={"email": "new@example.com"})

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "Validation failed."
    assert set(data["missing_fields"]) == {"full_name", "password"}


def test_register_weak_password_rejected(client):
    resp = client.post(
        URL, json={"full_name": "New User", "email": "new@example.com", "password": "short"}
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["invalid_fields"] == ["password"]


@pytest.mark.integration
def test_register_with_new_email_returns_token(client):
    email = f"{uuid.uuid4()}@example.com"

    resp = client.post(URL, json={"full_name": "New User", "email": email, "password": "Password123"})

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["token_type"] == "bearer"
    assert data["finish_profile_prompt"] is True


@pytest.mark.integration
def test_register_with_duplicate_email_rejected(client):
    email = f"{uuid.uuid4()}@example.com"
    client.post(URL, json={"full_name": "First User", "email": email, "password": "Password123"})

    resp = client.post(URL, json={"full_name": "Second User", "email": email, "password": "Password123"})

    assert resp.status_code == 409
    assert resp.get_json()["error"] == "Email already registered."

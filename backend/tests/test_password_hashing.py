"""Explicit constraints on password hashing: salted, non-reversible, and
the register endpoint's minimum-length rule enforced before a hash is ever
computed."""

from werkzeug.security import check_password_hash, generate_password_hash


def test_hash_is_not_plaintext():
    password = "Password123"
    hashed = generate_password_hash(password)

    assert hashed != password
    assert password not in hashed


def test_hash_is_salted_and_nondeterministic():
    password = "Password123"

    first = generate_password_hash(password)
    second = generate_password_hash(password)

    assert first != second  # same input, different salt each call
    assert check_password_hash(first, password)
    assert check_password_hash(second, password)


def test_check_password_hash_rejects_wrong_password():
    hashed = generate_password_hash("Password123")

    assert check_password_hash(hashed, "WrongPassword") is False


def test_register_rejects_password_under_minimum_length(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Fake User", "email": "short@example.com", "password": "short"},
    )

    assert resp.status_code == 400
    assert resp.get_json()["invalid_fields"] == ["password"]

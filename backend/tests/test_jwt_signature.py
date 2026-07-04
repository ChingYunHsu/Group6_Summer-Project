"""Explicit constraints on JWT signature generation/verification: correct
claims, correct algorithm/secret round-trip, and rejection of a token
signed with a different secret (i.e. signature forgery)."""

import jwt
import pytest

from auth import ACCESS_TOKEN_TTL, issue_access_token


def test_issued_token_has_expected_claims(app):
    with app.app_context():
        token = issue_access_token("u_1001")
        decoded = jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])

    assert decoded["sub"] == "u_1001"
    assert decoded["exp"] - decoded["iat"] == int(ACCESS_TOKEN_TTL.total_seconds())


def test_issued_token_uses_hs256(app):
    with app.app_context():
        token = issue_access_token("u_1001")

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256"


def test_token_signed_with_wrong_secret_is_rejected(app):
    with app.app_context():
        token = jwt.encode(
            {"sub": "u_1001", "exp": 9999999999}, "a-different-secret", algorithm="HS256"
        )

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])


def test_forged_token_rejected_by_bearer_auth_route(client, app):
    with app.app_context():
        forged = jwt.encode({"sub": "u_1001", "exp": 9999999999}, "wrong-secret", algorithm="HS256")

    resp = client.get("/api/v1/user/medical-id", headers={"Authorization": f"Bearer {forged}"})

    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized. Invalid token."

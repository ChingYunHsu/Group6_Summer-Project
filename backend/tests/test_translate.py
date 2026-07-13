"""Unit tests for POST /api/v1/translate, with Gemini faked out."""

import api.translate as translate_module
from auth import issue_access_token


def _token_for(app, user_id="u_1001"):
    with app.app_context():
        return issue_access_token(user_id)


def test_translate_requires_bearer_token(client):
    resp = client.post("/api/v1/translate", json={"text": "Me duele el pecho"})
    assert resp.status_code == 401


def test_translate_missing_text_rejected(client, app):
    token = _token_for(app)
    resp = client.post(
        "/api/v1/translate", json={}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["missing_fields"] == ["text"]


def test_translate_happy_path(client, app, monkeypatch):
    monkeypatch.setattr(
        translate_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {"translatedText": "My chest hurts"},
    )

    token = _token_for(app)
    resp = client.post(
        "/api/v1/translate",
        json={"text": "Me duele el pecho", "sourceLanguage": "es", "targetLanguage": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["translatedText"] == "My chest hurts"
    assert body["sourceLanguage"] == "es"
    assert body["targetLanguage"] == "en"


def test_translate_defaults_target_language_to_en(client, app, monkeypatch):
    captured_prompt = {}

    def fake_generate(prompt):
        captured_prompt["prompt"] = prompt
        return {"translatedText": "Hello"}

    monkeypatch.setattr(translate_module.gemini_client, "generate_structured_reply", fake_generate)

    token = _token_for(app)
    resp = client.post(
        "/api/v1/translate",
        json={"text": "Hola", "sourceLanguage": "es"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["targetLanguage"] == "en"
    assert "'es'" in captured_prompt["prompt"]
    assert "'en'" in captured_prompt["prompt"]


def test_translate_fails_loudly_never_fabricates_a_translation(client, app, monkeypatch):
    def _raise(prompt):
        raise RuntimeError("GEMINI_API_KEY is not configured")

    monkeypatch.setattr(translate_module.gemini_client, "generate_structured_reply", _raise)

    token = _token_for(app)
    resp = client.post(
        "/api/v1/translate",
        json={"text": "I am having a severe allergic reaction", "sourceLanguage": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Must be an explicit error, never a 200 with fabricated/echoed text —
    # a wrong medical translation is worse than an obvious failure.
    assert resp.status_code == 503
    assert "error" in resp.get_json()
    assert "translatedText" not in resp.get_json()


def test_translate_malformed_gemini_response_fails_loudly(client, app, monkeypatch):
    # Gemini returned JSON but without the expected key.
    monkeypatch.setattr(
        translate_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {"unexpected_key": "value"},
    )

    token = _token_for(app)
    resp = client.post(
        "/api/v1/translate",
        json={"text": "Hola"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 503

"""Unit tests for the RAG chatbot: semantic retrieval against
venue_embeddings, grounded Gemini generation, and the mock fallback when
Gemini/DB is unreachable. Also locks in that the chatbot module has no
possible path to medical_profiles / user_medical_profiles."""

import json
from contextlib import contextmanager

import api.chatbot as chatbot_module


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, query, params=()):
        assert "venue_embeddings" in query
        assert "medical" not in query.lower()

    def fetchall(self):
        return self._rows


def test_chatbot_module_has_no_medical_data_import():
    """Static guarantee: the chatbot can't reach medical_profiles because it
    never imports medical_crypto and never queries a medical profile table.
    Checked via the AST (not a raw substring scan) so the guard comment
    explaining this constraint doesn't trip its own check."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(chatbot_module))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "medical_crypto" not in imported_names

    # Only check literal SQL passed to .execute(...) calls, not docstrings
    # (which legitimately explain this constraint using the same words).
    sql_literals = [
        arg.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        for arg in node.args
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]
    assert sql_literals  # sanity: the module does execute at least one query
    assert not any("medical_profile" in sql.lower() for sql in sql_literals)


def test_ask_chatbot_missing_message_rejected(client):
    resp = client.post("/api/v1/chatbot", json={})
    assert resp.status_code == 400
    assert resp.get_json()["missing_fields"] == ["message"]


def test_ask_chatbot_rag_happy_path(client, monkeypatch):
    rows = [
    {
        "venue_id": "v_close_match",
        "embedding": json.dumps([1.0, 0.0]),
        "text_snapshot": "Central Park Urgent Care, open 24/7, wheelchair accessible.",
    },
    {
        "venue_id": "v_far_match",
        "embedding": json.dumps([0.0, 1.0]),
        "text_snapshot": "Uptown Pharmacy, closed on Sundays.",
    },
]

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor(rows)

    monkeypatch.setattr(chatbot_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        chatbot_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {
            "message": "Central Park Urgent Care is open 24/7 and wheelchair accessible.",
            "detected_language": "en",
        },
    )

    resp = client.post("/api/v1/chatbot", json={"message": "Is there a 24/7 clinic nearby?"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "Central Park Urgent Care is open 24/7 and wheelchair accessible."
    assert body["detected_language"] == "en"
    assert body["language"] == "en"
    assert body["citations"] == ["venue:v_close_match", "venue:v_far_match"]
    assert body["suggested_prompts"]
    assert body["fallback_used"] is False
    assert isinstance(body["response_time_ms"], int)


def test_ask_chatbot_suggested_prompts_match_detected_language(client, monkeypatch):
    """The suggested follow-up prompts must be localized to whatever
    language Gemini detected the user wrote in, not hardcoded English."""

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([])

    monkeypatch.setattr(chatbot_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        chatbot_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {
            "message": "Le Central Park Urgent Care est ouvert 24/7.",
            "detected_language": "fr",
        },
    )

    resp = client.post("/api/v1/chatbot", json={"message": "Y a-t-il une clinique 24/7 pres d'ici ?"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["detected_language"] == "fr"
    assert body["suggested_prompts"] == chatbot_module.SUGGESTED_PROMPTS_BY_LANGUAGE["fr"]


def test_ask_chatbot_suggested_prompts_follow_ui_language_not_message_language(client, monkeypatch):
    """The client's selected app-UI language (sent as `language` in the
    request) drives suggested_prompts, even when the user types a message
    in a different language than their UI is set to."""

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([])

    monkeypatch.setattr(chatbot_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        chatbot_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {
            "message": "Le Central Park Urgent Care est ouvert 24/7.",
            "detected_language": "fr",
        },
    )

    resp = client.post(
        "/api/v1/chatbot",
        json={"message": "Y a-t-il une clinique 24/7 pres d'ici ?", "language": "es"},
    )

    body = resp.get_json()
    assert body["detected_language"] == "fr"
    assert body["suggested_prompts"] == chatbot_module.SUGGESTED_PROMPTS_BY_LANGUAGE["es"]


def test_ask_chatbot_suggested_prompts_fall_back_to_english_for_unknown_language(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([])

    monkeypatch.setattr(chatbot_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        chatbot_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {"message": "...", "detected_language": "xx"},
    )

    resp = client.post("/api/v1/chatbot", json={"message": "hello"})

    assert resp.get_json()["suggested_prompts"] == chatbot_module.SUGGESTED_PROMPTS_BY_LANGUAGE["en"]


def test_ask_chatbot_grounded_prompt_only_uses_retrieved_context(monkeypatch):
    retrieved = [(0.9, "v_1", "Venue One is open 9-5."), (0.5, "v_2", "Venue Two has a wheelchair ramp.")]
    prompt = chatbot_module._build_grounded_prompt("When is Venue One open?", retrieved)

    assert "Venue One is open 9-5." in prompt
    assert "Venue Two has a wheelchair ramp." in prompt
    assert "When is Venue One open?" in prompt
    assert "Do not invent venues" in prompt


def test_ask_chatbot_falls_back_to_mock_when_gemini_unreachable(client, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise RuntimeError("GEMINI_API_KEY is not configured")

    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", _raise)

    resp = client.post("/api/v1/chatbot", json={"message": "Hello"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["fallback_used"] is True
    assert "message" in body
    assert "detected_language" in body


def test_ask_chatbot_falls_back_when_no_venues_match(client, monkeypatch):
    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([])

    monkeypatch.setattr(chatbot_module, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(chatbot_module.gemini_client, "embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        chatbot_module.gemini_client,
        "generate_structured_reply",
        lambda prompt: {"message": "I don't have information on that.", "detected_language": "en"},
    )

    resp = client.post("/api/v1/chatbot", json={"message": "Anything?"})

    assert resp.status_code == 200
    assert resp.get_json()["citations"] == []

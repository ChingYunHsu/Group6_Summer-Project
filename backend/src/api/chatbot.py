import json as _json
import math
import time
from copy import deepcopy

from flask import Blueprint, jsonify, request

import gemini_client
from auth import require_api_key
from db import db_cursor
from mock_data import CHATBOT_RESPONSE


bp = Blueprint("chatbot", __name__)

TOP_K_VENUES = 3

SUGGESTED_PROMPTS = [
    "Find an urgent care near me",
    "Which clinics are open now?",
    "I have no insurance",
]

# The chatbot must NEVER have a path to medical_profiles / user_medical_profiles
# (encrypted health data). It only ever queries venue_embeddings below —
# do not add a medical_profiles/medical_crypto import to this module.
_RAG_SYSTEM_INSTRUCTIONS = (
    "You are ClearPath's assistant for vulnerable tourists seeking healthcare "
    "in Manhattan. Answer ONLY using the operational venue information given "
    "below as context. Do not invent venues, hours, capacity, or capabilities "
    "not present in that context. If the context doesn't answer the question, "
    "say so plainly rather than guessing.\n\n"
    'Respond with a single JSON object with exactly two keys: "message" (your '
    "answer, written in the same language as the user's question) and "
    '"detected_language" (the ISO 639-1 code of the language the user wrote '
    'in, e.g. "en", "es", "fr", "zh").'
)


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _retrieve_relevant_venues(cursor, query_embedding: list, top_k: int = TOP_K_VENUES) -> list:
    """Semantic retrieval against venue_embeddings ONLY. Returns
    [(score, venue_id, text_snapshot), ...] sorted by similarity descending."""
    cursor.execute("SELECT venue_id, embedding, text_snapshot FROM venue_embeddings")
    rows = cursor.fetchall()

    scored = []
    for row in rows:
        venue_id = row["venue_id"]
        embedding_raw = row["embedding"]
        text_snapshot = row["text_snapshot"]
        embedding = _json.loads(embedding_raw) if isinstance(embedding_raw, str) else embedding_raw
        scored.append((_cosine_similarity(query_embedding, embedding), venue_id, text_snapshot))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def _build_grounded_prompt(message: str, retrieved: list) -> str:
    context_block = "\n".join(f"- ({venue_id}): {snippet}" for _score, venue_id, snippet in retrieved) or "(no matching venues found)"
    return f"{_RAG_SYSTEM_INSTRUCTIONS}\n\nVenue context:\n{context_block}\n\nUser question: {message}"


def _ask_gemini_rag(message: str) -> dict:
    """Full RAG pipeline: embed the query, retrieve grounded venue context
    from venue_embeddings, generate a structured response. Only ever touches
    venue_embeddings — no medical_profiles access is possible from here."""
    start = time.monotonic()

    query_embedding = gemini_client.embed_text(message)

    with db_cursor() as cursor:
        retrieved = _retrieve_relevant_venues(cursor, query_embedding)

    prompt = _build_grounded_prompt(message, retrieved)
    structured = gemini_client.generate_structured_reply(prompt)

    reply_text = structured["message"]
    detected_language = structured.get("detected_language", "en")
    citations = [f"venue:{venue_id}" for _score, venue_id, _snippet in retrieved]

    return {
        "message": reply_text,
        "language": detected_language,
        "detected_language": detected_language,
        "citations": citations,
        "suggested_prompts": SUGGESTED_PROMPTS,
        "fallback_used": False,
        "response_time_ms": round((time.monotonic() - start) * 1000),
    }


@bp.post("/api/v1/chatbot")
@require_api_key
def ask_chatbot():
    payload = request.get_json(silent=True) or {}

    if "message" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["message"]}), 400

    try:
        return jsonify(_ask_gemini_rag(payload["message"]))
    except Exception:
        pass  # Fallback to mock data below.

    response = deepcopy(CHATBOT_RESPONSE)
    response.setdefault("detected_language", response.get("language", "en"))
    if "language" in payload:
        response["language"] = payload["language"]
    response["fallback_used"] = True

    return jsonify(response)

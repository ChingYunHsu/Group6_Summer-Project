import json as _json
import math
import time
from copy import deepcopy

from flask import Blueprint, current_app, jsonify, request

import gemini_client
from auth import require_api_key
from db import db_cursor
from mock_data import CHATBOT_RESPONSE


bp = Blueprint("chatbot", __name__)

TOP_K_VENUES = 3

SUGGESTED_PROMPTS_BY_LANGUAGE = {
    "en": [
        "Find an urgent care near me",
        "Which clinics are open now?",
        "I have no insurance",
    ],
    "de": [
        "Finde eine Notfallklinik in meiner Nähe",
        "Welche Kliniken haben jetzt geöffnet?",
        "Ich habe keine Versicherung",
    ],
    "fr": [
        "Trouver un centre de soins d'urgence près de moi",
        "Quelles cliniques sont ouvertes maintenant ?",
        "Je n'ai pas d'assurance",
    ],
    "it": [
        "Trova un pronto soccorso vicino a me",
        "Quali cliniche sono aperte ora?",
        "Non ho un'assicurazione",
    ],
    "es": [
        "Encontrar atención de urgencia cerca de mí",
        "¿Qué clínicas están abiertas ahora?",
        "No tengo seguro médico",
    ],
    "zh": [
        "查找附近的紧急护理中心",
        "现在哪些诊所营业？",
        "我没有保险",
    ],
}


def _suggested_prompts(language: str) -> list:
    return SUGGESTED_PROMPTS_BY_LANGUAGE.get(language, SUGGESTED_PROMPTS_BY_LANGUAGE["en"])


# The chatbot must NEVER have a path to medical_profiles / user_medical_profiles
# (encrypted health data). It only ever queries venue_embeddings/venues below —
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


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _retrieve_relevant_venues(
    cursor,
    query_embedding: list,
    user_lat: float | None = None,
    user_lon: float | None = None,
    top_k: int = TOP_K_VENUES,
) -> list:
    # Joined to venues so distance can be computed - venue_embeddings alone
    # has no coordinates.
    cursor.execute(
        "SELECT ve.venue_id, ve.embedding, ve.text_snapshot, "
        "v.latitude, v.longitude "
        "FROM venue_embeddings ve "
        "JOIN venues v ON v.venue_id = ve.venue_id"
    )
    rows = cursor.fetchall()

    scored = []
    for row in rows:
        venue_id = row["venue_id"]
        embedding_raw = row["embedding"]
        text_snapshot = row["text_snapshot"]
        embedding = (
            _json.loads(embedding_raw)
            if isinstance(embedding_raw, str)
            else embedding_raw
        )

        distance_km = None
        venue_lat = row.get("latitude")
        venue_lon = row.get("longitude")
        if (
            user_lat is not None
            and user_lon is not None
            and venue_lat is not None
            and venue_lon is not None
        ):
            # MySQL DECIMAL columns come back from pymysql as decimal.Decimal,
            # which can't be mixed with float in arithmetic - cast both sides.
            distance_km = _haversine_km(
                float(user_lat), float(user_lon), float(venue_lat), float(venue_lon)
            )

        scored.append(
            (
                _cosine_similarity(query_embedding, embedding),
                venue_id,
                text_snapshot,
                distance_km,
            )
        )

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def _build_grounded_prompt(
    message: str,
    retrieved: list,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> str:
    lines = []
    for _score, venue_id, snippet, distance_km in retrieved:
        distance_str = (
            f", ~{distance_km:.1f} km from the user" if distance_km is not None else ""
        )
        lines.append(f"- ({venue_id}){distance_str}: {snippet}")

    context_block = "\n".join(lines) or "(no matching venues found)"

    location_note = (
        "The user's current coordinates were provided, and the distance shown "
        "next to each venue above is computed from them."
        if user_lat is not None and user_lon is not None
        else "The user's location was not provided, so you cannot determine "
        "proximity to any venue - say so plainly if asked about distance."
    )

    return (
        f"{_RAG_SYSTEM_INSTRUCTIONS}\n\n{location_note}\n\n"
        f"Venue context:\n{context_block}\n\nUser question: {message}"
    )


def _ask_gemini_rag(
    message: str,
    ui_language: str = None,
    user_lat: float = None,
    user_lon: float = None,
) -> dict:
    """Full RAG pipeline: embed the query, retrieve grounded venue context
    from venue_embeddings joined to venues, generate a structured response.
    Only ever touches venue_embeddings/venues - no medical_profiles access
    is possible from here.

    `ui_language` is the client's selected app-UI language (from signup/
    settings), used only to pick suggested_prompts - it's independent of
    detected_language, which is Gemini's per-message detection of whatever
    language the user actually typed in and always drives `message`/`language`.

    `user_lat`/`user_lon` are the device's current coordinates, sent fresh
    on every request from the client - used only to compute distance for
    the grounded prompt context, never stored.
    """
    start = time.monotonic()

    query_embedding = gemini_client.embed_text(message)

    with db_cursor() as cursor:
        retrieved = _retrieve_relevant_venues(cursor, query_embedding, user_lat, user_lon)

    prompt = _build_grounded_prompt(message, retrieved, user_lat, user_lon)
    structured = gemini_client.generate_structured_reply(prompt)

    reply_text = structured["message"]
    detected_language = structured.get("detected_language", "en")
    citations = [f"venue:{venue_id}" for _score, venue_id, _snippet, _distance in retrieved]

    return {
        "message": reply_text,
        "language": detected_language,
        "detected_language": detected_language,
        "citations": citations,
        "suggested_prompts": _suggested_prompts(ui_language or detected_language),
        "fallback_used": False,
        "response_time_ms": round((time.monotonic() - start) * 1000),
    }


@bp.post("/api/v1/chatbot")
@require_api_key
def ask_chatbot():
    payload = request.get_json(silent=True) or {}

    message = payload.get("message")

    if not isinstance(message, str) or not message.strip():
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "missing_fields": ["message"],
                }
            ),
            400,
        )

    fallback_reason = None

    try:
        return jsonify(
            _ask_gemini_rag(
                message.strip(),
                payload.get("language"),
                payload.get("latitude"),
                payload.get("longitude"),
            )
        )

    except Exception as error:
        fallback_reason = (
            f"{type(error).__name__}: {error}"
        )

        current_app.logger.exception(
            "Chatbot RAG pipeline failed: %s",
            fallback_reason,
        )

    response = deepcopy(CHATBOT_RESPONSE)

    fallback_language = payload.get(
        "language",
        "en",
    )

    if (
        fallback_language
        not in SUGGESTED_PROMPTS_BY_LANGUAGE
    ):
        fallback_language = "en"

    response["language"] = fallback_language
    response["detected_language"] = fallback_language
    response["suggested_prompts"] = _suggested_prompts(
        fallback_language
    )
    response["fallback_used"] = True

    # Only expose this during local development.
    if current_app.debug and fallback_reason:
        response["fallback_reason"] = fallback_reason

    return jsonify(response)
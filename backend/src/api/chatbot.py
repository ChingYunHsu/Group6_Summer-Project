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
SEMANTIC_CANDIDATE_COUNT = 30

# The web map and chatbot intentionally use the same fixed demonstration
# location. Incoming client coordinates are ignored so the chatbot never
# asks for, stores, or relies on a user's real location.
MOCK_USER_LATITUDE = 40.758
MOCK_USER_LONGITUDE = -73.9855


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


def _normalise_language_code(language: str | None) -> str:
    code = str(language or "en").strip().lower()
    code = code.split("-", maxsplit=1)[0]
    code = code.split("_", maxsplit=1)[0]

    if code in SUGGESTED_PROMPTS_BY_LANGUAGE:
        return code

    return "en"


def _suggested_prompts(language: str | None) -> list:
    code = _normalise_language_code(language)
    return SUGGESTED_PROMPTS_BY_LANGUAGE[code]


# The chatbot must NEVER have a path to medical_profiles /
# user_medical_profiles (encrypted health data). It only ever queries
# venue_embeddings and venues below. Do not add a medical-profile or
# medical-crypto import to this module.
_RAG_SYSTEM_INSTRUCTIONS = (
    "You are ClearPath's assistant for vulnerable tourists seeking healthcare "
    "and accessibility support in Manhattan. Answer ONLY using the operational "
    "venue information provided below as context. Do not invent venues, hours, "
    "capacity, distance, accessibility, insurance acceptance, or capabilities "
    "that are not present in that context. If the context does not answer the "
    "question, say so plainly rather than guessing. Distances, when present, "
    "are measured from ClearPath's fixed demonstration location and not from "
    "the user's real location. Never ask the user to provide their location.\n\n"
    'Respond with a single JSON object with exactly two keys: "message" '
    "(your answer, written in the same language as the user's question) and "
    '"detected_language" (the ISO 639-1 code of the language the user wrote '
    'in, for example "en", "de", "fr", "it", "es", or "zh").'
)


# Query terms include the languages currently supported by ClearPath.
QUERY_CATEGORY_TERMS = {
    "hospital": (
        "hospital",
        "emergency room",
        "medical center",
        "medical centre",
        "krankenhaus",
        "notaufnahme",
        "hôpital",
        "hopital",
        "urgences",
        "ospedale",
        "pronto soccorso",
        "hospital",
        "urgencias",
        "医院",
        "急诊",
    ),
    "pharmacy": (
        "pharmacy",
        "chemist",
        "drugstore",
        "apotheke",
        "pharmacie",
        "farmacia",
        "药房",
        "药店",
    ),
    "clinic": (
        "clinic",
        "urgent care",
        "health center",
        "health centre",
        "klinik",
        "notfallklinik",
        "clinique",
        "centre de soins",
        "clinica",
        "clínica",
        "诊所",
        "紧急护理",
    ),
    "restroom": (
        "restroom",
        "toilet",
        "bathroom",
        "wc",
        "toilette",
        "toilettes",
        "bagno",
        "baño",
        "bano",
        "卫生间",
        "厕所",
    ),
    "aed": (
        "aed",
        "defibrillator",
        "defibrillateur",
        "défibrillateur",
        "defibrillatore",
        "desfibrilador",
        "自动体外除颤器",
        "除颤器",
    ),
}


# Venue snapshots are produced by backfill_venue_embeddings.py and generally
# contain English venue types plus the venue's proper name.
SNAPSHOT_CATEGORY_TERMS = {
    "hospital": (
        "hospital",
        "medical center",
        "medical centre",
        "emergency room",
        "infirmary",
    ),
    "pharmacy": (
        "pharmacy",
        "chemist",
        "drugstore",
        "drug store",
    ),
    "clinic": (
        "clinic",
        "urgent care",
        "health center",
        "health centre",
        "healthcare",
    ),
    "restroom": (
        "restroom",
        "toilet",
        "bathroom",
    ),
    "aed": (
        "aed",
        "defibrillator",
        "emergencyasset",
        "emergency asset",
    ),
}


PROXIMITY_TERMS = (
    "nearest",
    "closest",
    "near me",
    "nearby",
    "how far",
    "distance",
    "nächste",
    "nächsten",
    "in meiner nähe",
    "près de moi",
    "proche",
    "le plus proche",
    "vicino a me",
    "più vicino",
    "piu vicino",
    "cerca de mí",
    "cerca de mi",
    "más cercano",
    "mas cercano",
    "附近",
    "最近",
    "多远",
)


def _requested_category(message: str) -> str | None:
    cleaned_message = str(message or "").strip().lower()

    for category, terms in QUERY_CATEGORY_TERMS.items():
        if any(term in cleaned_message for term in terms):
            return category

    return None


def _query_requests_proximity(message: str) -> bool:
    cleaned_message = str(message or "").strip().lower()
    return any(term in cleaned_message for term in PROXIMITY_TERMS)


def _row_matches_category(row: dict, category: str | None) -> bool:
    if not category:
        return True

    searchable_text = " ".join(
        str(value)
        for value in (
            row.get("name"),
            row.get("venue_type"),
            row.get("text_snapshot"),
        )
        if value
    ).lower()

    return any(
        term in searchable_text
        for term in SNAPSHOT_CATEGORY_TERMS[category]
    )


def _cosine_similarity(a: list, b: list) -> float:
    if not isinstance(a, list) or not isinstance(b, list):
        return 0.0

    if not a or not b or len(a) != len(b):
        return 0.0

    try:
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
        norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    except (TypeError, ValueError):
        return 0.0

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_km = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    delta_latitude = math.radians(lat2 - lat1)
    delta_longitude = math.radians(lon2 - lon1)

    haversine_value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(delta_longitude / 2) ** 2
    )

    return (
        2
        * earth_radius_km
        * math.asin(math.sqrt(haversine_value))
    )


def _parse_embedding(
    embedding_raw,
    venue_id: str,
) -> list | None:
    if embedding_raw is None:
        current_app.logger.warning(
            "Skipping venue %s because its embedding is null",
            venue_id,
        )
        return None

    try:
        embedding = (
            _json.loads(embedding_raw)
            if isinstance(embedding_raw, str)
            else embedding_raw
        )
    except (TypeError, ValueError, _json.JSONDecodeError):
        current_app.logger.warning(
            "Skipping venue %s because its embedding JSON is malformed",
            venue_id,
        )
        return None

    if not isinstance(embedding, list) or not embedding:
        current_app.logger.warning(
            "Skipping venue %s because its embedding is empty",
            venue_id,
        )
        return None

    return embedding


def _retrieve_relevant_venues(
    cursor,
    query_embedding: list,
    message: str,
    user_lat: float = MOCK_USER_LATITUDE,
    user_lon: float = MOCK_USER_LONGITUDE,
    top_k: int = TOP_K_VENUES,
) -> list:
    """Retrieve grounded venue context for one chatbot question.

    Explicit categories such as hospital, pharmacy, clinic, restroom, or AED
    are applied before ranking. Proximity questions are then ranked by
    distance from ClearPath's fixed demonstration location.
    """
    cursor.execute(
        "SELECT "
        "ve.venue_id, "
        "ve.embedding, "
        "ve.text_snapshot, "
        "v.name, "
        "v.venue_type, "
        "v.latitude, "
        "v.longitude "
        "FROM venue_embeddings ve "
        "JOIN venues v ON v.venue_id = ve.venue_id"
    )

    rows = cursor.fetchall()
    requested_category = _requested_category(message)
    proximity_requested = _query_requests_proximity(message)

    scored = []

    for row in rows:
        venue_id = row["venue_id"]

        if not _row_matches_category(row, requested_category):
            continue

        embedding = _parse_embedding(
            row.get("embedding"),
            venue_id,
        )

        if embedding is None:
            continue

        similarity = _cosine_similarity(
            query_embedding,
            embedding,
        )

        # A zero score can also indicate mismatched embedding dimensions.
        if similarity == 0.0 and len(query_embedding) != len(embedding):
            current_app.logger.warning(
                "Skipping venue %s because embedding dimensions differ "
                "(query=%s, stored=%s)",
                venue_id,
                len(query_embedding),
                len(embedding),
            )
            continue

        distance_km = None
        venue_lat = row.get("latitude")
        venue_lon = row.get("longitude")

        if venue_lat is not None and venue_lon is not None:
            try:
                distance_km = _haversine_km(
                    float(user_lat),
                    float(user_lon),
                    float(venue_lat),
                    float(venue_lon),
                )
            except (TypeError, ValueError):
                current_app.logger.warning(
                    "Venue %s has invalid coordinates: latitude=%r longitude=%r",
                    venue_id,
                    venue_lat,
                    venue_lon,
                )

        scored.append(
            (
                similarity,
                venue_id,
                row.get("text_snapshot") or "",
                distance_km,
            )
        )

    # Begin with semantic relevance.
    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # For an explicit "nearest" request within a recognised category, all
    # matching category venues remain eligible before distance sorting.
    # Otherwise, distance only reorders a broader semantic shortlist.
    if requested_category and proximity_requested:
        candidates = scored
    else:
        candidates = scored[:SEMANTIC_CANDIDATE_COUNT]

    if proximity_requested:
        candidates.sort(
            key=lambda item: (
                item[3] is None,
                (
                    item[3]
                    if item[3] is not None
                    else float("inf")
                ),
                -item[0],
            )
        )

    retrieved = candidates[:top_k]

    current_app.logger.info(
        "Chatbot retrieval: query=%r category=%r proximity=%s "
        "mock_location=(%.6f, %.6f) retrieved=%s",
        message,
        requested_category,
        proximity_requested,
        user_lat,
        user_lon,
        [
            {
                "score": round(score, 4),
                "venue_id": venue_id,
                "distance_km": (
                    round(distance_km, 2)
                    if distance_km is not None
                    else None
                ),
                "snapshot": snippet[:200],
            }
            for (
                score,
                venue_id,
                snippet,
                distance_km,
            ) in retrieved
        ],
    )

    return retrieved


def _build_grounded_prompt(
    message: str,
    retrieved: list,
    user_lat: float = MOCK_USER_LATITUDE,
    user_lon: float = MOCK_USER_LONGITUDE,
) -> str:
    lines = []

    for (
        _score,
        venue_id,
        snippet,
        distance_km,
    ) in retrieved:
        distance_text = (
            f", approximately {distance_km:.1f} km from "
            "ClearPath's demonstration location"
            if distance_km is not None
            else ""
        )

        lines.append(
            f"- ({venue_id}){distance_text}: {snippet}"
        )

    context_block = (
        "\n".join(lines)
        if lines
        else "(no matching venues found)"
    )

    location_note = (
        "ClearPath is using its fixed demonstration location at "
        f"latitude {user_lat:.6f}, longitude {user_lon:.6f}. "
        "Any distances in the venue context are calculated from that mock "
        "location, not from the user's actual location. Do not ask the user "
        "to provide location access or coordinates."
    )

    return (
        f"{_RAG_SYSTEM_INSTRUCTIONS}\n\n"
        f"{location_note}\n\n"
        f"Venue context:\n{context_block}\n\n"
        f"User question: {message}"
    )


def _ask_gemini_rag(
    message: str,
    ui_language: str | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> dict:
    """Run the full venue-only RAG pipeline.

    The latitude and longitude parameters remain in the function signature for
    compatibility with existing callers, but are deliberately ignored. Every
    request uses ClearPath's fixed demonstration location.

    This function only queries venue_embeddings and venues. It has no access
    path to medical-profile data.
    """
    del user_lat, user_lon

    start = time.monotonic()
    stage = "validation"

    try:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")

        cleaned_message = message.strip()

        resolved_latitude = MOCK_USER_LATITUDE
        resolved_longitude = MOCK_USER_LONGITUDE

        stage = "embedding"
        query_embedding = gemini_client.embed_text(
            cleaned_message
        )

        stage = "venue retrieval"
        with db_cursor() as cursor:
            retrieved = _retrieve_relevant_venues(
                cursor,
                query_embedding,
                cleaned_message,
                resolved_latitude,
                resolved_longitude,
            )

        stage = "prompt construction"
        prompt = _build_grounded_prompt(
            cleaned_message,
            retrieved,
            resolved_latitude,
            resolved_longitude,
        )

        stage = "Gemini generation"
        structured = gemini_client.generate_structured_reply(
            prompt
        )

        stage = "response validation"
        reply_text = structured["message"]

        if not isinstance(reply_text, str) or not reply_text.strip():
            raise RuntimeError(
                "Gemini returned an empty chatbot message"
            )

        detected_language = _normalise_language_code(
            structured.get("detected_language")
        )

        citations = [
            f"venue:{venue_id}"
            for (
                _score,
                venue_id,
                _snippet,
                _distance,
            ) in retrieved
        ]

        return {
            "message": reply_text.strip(),
            "language": detected_language,
            "detected_language": detected_language,
            "citations": citations,
            "suggested_prompts": _suggested_prompts(
                ui_language or detected_language
            ),
            "fallback_used": False,
            "response_time_ms": round(
                (time.monotonic() - start) * 1000
            ),
        }

    except Exception as error:
        raise RuntimeError(
            f"Chatbot RAG failed during {stage}: {error}"
        ) from error


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

    fallback_language = _normalise_language_code(
        payload.get("language")
    )

    response["language"] = fallback_language
    response["detected_language"] = fallback_language
    response["suggested_prompts"] = _suggested_prompts(
        fallback_language
    )
    response["fallback_used"] = True

    # Expose the reason only in local Flask debug mode.
    if current_app.debug and fallback_reason:
        response["fallback_reason"] = fallback_reason

    return jsonify(response)
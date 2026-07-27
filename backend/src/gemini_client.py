"""Thin REST client for the Gemini API."""

import json
import os
from typing import Any

import requests
from flask import current_app

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
EMBEDDING_MODEL = "models/gemini-embedding-001"
GENERATION_MODEL = os.getenv(
    "GEMINI_GENERATION_MODEL",
    "models/gemini-3.5-flash-lite",
).strip()

REQUEST_TIMEOUT = (5, 45)


def _api_key() -> str:
    key = (
        current_app.config.get("GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    ).strip()

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Flask config or environment"
        )

    return key


def _post_to_gemini(
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        f"{GEMINI_API_BASE}/{endpoint}",
        headers={
            "x-goog-api-key": _api_key(),
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if not response.ok:
        current_app.logger.error(
            "Gemini request failed: endpoint=%s status=%s response=%s",
            endpoint,
            response.status_code,
            response.text[:2000],
        )

    response.raise_for_status()

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise RuntimeError(
            f"Gemini returned invalid JSON: {response.text[:500]}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Unexpected Gemini response type: {type(data).__name__}"
        )

    return data


def embed_text(text: str) -> list[float]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding text must be a non-empty string")

    response = _post_to_gemini(
        f"{EMBEDDING_MODEL}:embedContent",
        {
            "content": {
                "parts": [
                    {
                        "text": text.strip(),
                    }
                ]
            }
        },
    )

    embedding = response.get("embedding")
    values = (
        embedding.get("values")
        if isinstance(embedding, dict)
        else None
    )

    if not isinstance(values, list) or not values:
        raise RuntimeError(
            f"Gemini embedding response has no values: {response}"
        )

    return [float(value) for value in values]


def generate_structured_reply(prompt: str) -> dict[str, str]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Generation prompt must be a non-empty string")

    response = _post_to_gemini(
        f"{GENERATION_MODEL}:generateContent",
        {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt.strip(),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "message": {
                            "type": "STRING",
                        },
                        "detected_language": {
                            "type": "STRING",
                        },
                    },
                    "required": [
                        "message",
                        "detected_language",
                    ],
                },
                "maxOutputTokens": 512,
            },
        },
    )

    candidates = response.get("candidates")

    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError(
            "Gemini returned no candidates. "
            f"Prompt feedback: {response.get('promptFeedback')}"
        )

    candidate = candidates[0]
    content = candidate.get("content", {})
    parts = content.get("parts", [])

    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
    ).strip()

    if not text:
        raise RuntimeError(
            "Gemini returned no text. "
            f"Finish reason: {candidate.get('finishReason')}"
        )

    try:
        structured = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Gemini returned malformed JSON: {text[:500]}"
        ) from error

    message = structured.get("message")
    detected_language = structured.get(
        "detected_language",
        "en",
    )

    if not isinstance(message, str) or not message.strip():
        raise RuntimeError(
            "Gemini response did not contain a valid message"
        )

    if not isinstance(detected_language, str):
        detected_language = "en"

    return {
        "message": message.strip(),
        "detected_language": detected_language.strip().lower(),
    }
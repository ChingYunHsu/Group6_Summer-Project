"""Thin REST client for the Gemini API (embeddings + generation).

Uses `requests` directly against the public REST endpoints rather than
pulling in the full google-generativeai SDK, since this is the only
Gemini call site in the backend. Both calls raise on any failure (network,
auth, malformed response) — callers are expected to catch and fall back,
matching the resilience pattern used elsewhere in this API (see
api/venues.py's DB-then-mock fallback).
"""

import json

import requests
from flask import current_app

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
EMBEDDING_MODEL = "models/text-embedding-004"
GENERATION_MODEL = "models/gemini-1.5-flash"
REQUEST_TIMEOUT_SECONDS = 8


def _api_key() -> str:
    key = current_app.config.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return key


def embed_text(text: str) -> list:
    """Return the embedding vector for `text` via Gemini's embedding model."""
    resp = requests.post(
        f"{GEMINI_API_BASE}/{EMBEDDING_MODEL}:embedContent",
        params={"key": _api_key()},
        json={"content": {"parts": [{"text": text}]}},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


def generate_structured_reply(prompt: str) -> dict:
    """Ask Gemini to answer strictly in JSON (see the prompt's own schema
    instructions) and return the parsed dict. Raises if the model didn't
    return valid JSON — callers fall back to the mock response rather than
    guessing at malformed model output."""
    resp = requests.post(
        f"{GEMINI_API_BASE}/{GENERATION_MODEL}:generateContent",
        params={"key": _api_key()},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)

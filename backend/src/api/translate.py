"""Server-side text translation for the mobile app's Live Translate feature
(frontend/mobile/.../show-staff.tsx) — translates arbitrary visitor input
that isn't covered by the canned phraseTemplates. Done server-side so the
Gemini API key never ships in the client bundle.

This is patient/staff emergency communication — a wrong-but-confident
"translation" is actively dangerous, worse than no translation at all. On
any failure this returns an error rather than falling back to a mock/echo
response, unlike most other endpoints in this API.
"""

from flask import Blueprint, jsonify, request

import gemini_client
from auth import require_bearer_auth


bp = Blueprint("translate", __name__)

DEFAULT_TARGET_LANGUAGE = "en"


def _build_translation_prompt(text: str, source_language: str, target_language: str) -> str:
    return (
        f"Translate the following text from language code '{source_language}' "
        f"to language code '{target_language}'. This may be spoken by a "
        "vulnerable tourist describing a medical or emergency situation to "
        "hospital/clinic staff — translate literally and precisely, do not "
        "soften, summarize, or omit anything.\n\n"
        'Respond with a single JSON object with exactly one key: "translatedText" '
        "(the translation only — no explanation, no quotes around it, no "
        "commentary).\n\n"
        f"Text: {text}"
    )


@bp.post("/api/v1/translate")
@require_bearer_auth
def translate_text():
    payload = request.get_json(silent=True) or {}

    if "text" not in payload:
        return jsonify({"error": "Validation failed.", "missing_fields": ["text"]}), 400

    text = payload["text"]
    source_language = payload.get("sourceLanguage") or "auto"
    target_language = payload.get("targetLanguage") or DEFAULT_TARGET_LANGUAGE

    try:
        prompt = _build_translation_prompt(text, source_language, target_language)
        result = gemini_client.generate_structured_reply(prompt)
        translated_text = result["translatedText"]
    except Exception:
        return jsonify({"error": "Translation is temporarily unavailable. Please try again."}), 503

    return jsonify(
        {
            "translatedText": translated_text,
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
        }
    )

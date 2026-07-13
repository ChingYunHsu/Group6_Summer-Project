// Matches POST /api/v1/translate's real response shape
// (backend/src/api/translate.py). There is no mock/fallback path on this
// endpoint — a failure always means an actual error response (400 for
// missing text, 503 if Gemini itself fails), never a fabricated
// translation, since a wrong medical translation is worse than an
// obvious failure.
export interface TranslateResponse {
  translatedText: string;

  sourceLanguage: string;

  targetLanguage: string;
}

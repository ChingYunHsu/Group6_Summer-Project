export interface ChatbotResponse {
  message: string;

  language: string;

  // Sent by the real (non-fallback) RAG path specifically — see
  // _ask_gemini_rag in chatbot.py. Optional since older/mock responses
  // may not include it.
  detected_language?: string;

  // Bare identifiers like "venue:v_1001", not resolved content — the
  // client has to parse and look these up itself. See parseCitation() in
  // assistant.tsx.
  citations: string[];

  suggested_prompts: string[];

  fallback_used: boolean;

  response_time_ms: number;
}

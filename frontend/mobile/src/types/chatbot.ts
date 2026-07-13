export interface ChatbotResponse {
  message: string;

  language: string;

  // Bare identifiers like "venue:v_1001", not resolved content — the
  // client has to parse and look these up itself. See parseCitation() in
  // assistant.tsx.
  citations: string[];

  suggested_prompts: string[];

  fallback_used: boolean;

  response_time_ms: number;
}

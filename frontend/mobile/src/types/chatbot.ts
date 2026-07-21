export interface ChatbotResponse {
  message: string;

  language: string;

  detected_language?: string;

  citations: string[];

  suggested_prompts: string[];

  fallback_used: boolean;

  response_time_ms: number;
}

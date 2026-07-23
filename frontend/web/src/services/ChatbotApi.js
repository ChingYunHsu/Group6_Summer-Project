const DEFAULT_API_KEY = "development";

function buildHeaders(extraHeaders = {}) {
  const headers = new Headers(extraHeaders);
  const apiKey = import.meta.env.VITE_API_KEY || DEFAULT_API_KEY;
  const accessToken = localStorage.getItem("access_token");

  headers.set("Accept", "application/json");
  headers.set("Content-Type", "application/json");
  headers.set("X-Client-Origin", "web");

  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function chatbotRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: buildHeaders(options.headers),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload?.message ||
      payload?.error ||
      payload?.detail ||
      `Request failed with status ${response.status}`;

    const requestError = new Error(message);
    requestError.status = response.status;
    requestError.payload = payload;

    throw requestError;
  }

  return payload;
}

export async function sendChatbotMessage({ message, language } = {}) {
  return chatbotRequest("/api/v1/chatbot", {
    method: "POST",
    body: JSON.stringify({ message, language }),
  });
}
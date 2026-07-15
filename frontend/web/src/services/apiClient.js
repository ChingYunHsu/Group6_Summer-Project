import { getAccessToken, clearAuthData } from "./tokenStorage";

const API_KEY = import.meta.env.VITE_API_KEY || "development";

export async function apiRequest(endpoint, options = {}) {
  const token = getAccessToken();

  const response = await fetch(`/api/v1${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,

      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),

      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();

    const parsedBody = await response
      .json()
      .catch(() => null);
    
      if (response.status === 401) {
      clearAuthData();
    }

    const error = new Error(
      parsedBody?.error || `API ${response.status}: ${text}`
    );

    error.status = response.status;
    error.body = parsedBody;

    throw error;
  }

  if (response.status === 204) {
    return undefined;
  }

  return response.json();
}
const DEFAULT_API_KEY = "development";

function buildHeaders(extraHeaders = {}) {
  const headers = new Headers(extraHeaders);
  const apiKey = import.meta.env.VITE_API_KEY || DEFAULT_API_KEY;
  const accessToken = localStorage.getItem("access_token");

  headers.set("Accept", "application/json");
  headers.set("X-Client-Origin", "web");

  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function insightsRequest(path, options = {}) {
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

function unwrapInsightsPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return {};
  }

  const possibleKeys = [
    "insights",
    "dashboard",
    "result",
    "data",
  ];

  for (const key of possibleKeys) {
    if (
      payload[key] &&
      typeof payload[key] === "object" &&
      !Array.isArray(payload[key])
    ) {
      return payload[key];
    }
  }

  return payload;
}

export async function getInsightsDashboard({
  district,
  latitude,
  longitude,
} = {}) {
  const params = new URLSearchParams();

  if (district) {
    params.set("district", district);
  }

  if (
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude))
  ) {
    params.set("lat", String(latitude));
    params.set("lon", String(longitude));
  }

  const query = params.toString();
  const payload = await insightsRequest(
    `/api/v1/insights${query ? `?${query}` : ""}`
  );

  return unwrapInsightsPayload(payload);
}

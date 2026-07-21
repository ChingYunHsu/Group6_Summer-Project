const DEFAULT_API_KEY = "development";

function getHeaders(extraHeaders = {}) {
  const headers = new Headers(extraHeaders);
  const apiKey = import.meta.env.VITE_API_KEY || DEFAULT_API_KEY;
  const accessToken = localStorage.getItem("access_token");

  headers.set("Accept", "application/json");
  headers.set("X-API-Key", apiKey);
  headers.set("X-Client-Origin", "web");

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: getHeaders(options.headers),
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

function unwrapArray(payload, possibleKeys) {
  if (Array.isArray(payload)) return payload;

  for (const key of possibleKeys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }

  return [];
}

function unwrapObject(payload, possibleKeys) {
  if (!payload || typeof payload !== "object") return {};

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

export async function listVenues({
  languages,
  accessible,
  openNow,
  venueType,
} = {}) {
  const params = new URLSearchParams();

  if (languages?.length) {
    params.set("languages", languages.join(","));
  }

  if (accessible) {
    params.set("accessible", "true");
  }

  if (openNow) {
    params.set("open_now", "true");
  }

  if (venueType) {
    params.set("venue_type", venueType);
  }

  const query = params.toString();
  const payload = await apiRequest(
    `/api/v1/venues${query ? `?${query}` : ""}`
  );

  return unwrapArray(payload, ["venues", "items", "results", "data"]);
}

export async function getVenueById(venueId) {
  const payload = await apiRequest(
    `/api/v1/venues/${encodeURIComponent(venueId)}`
  );

  return unwrapObject(payload, ["venue", "data"]);
}

export async function getVenueBusyness(venueId, queryTime = "") {
  const params = new URLSearchParams();

  if (queryTime) {
    params.set("query_time", queryTime);
  }

  const query = params.toString();
  const payload = await apiRequest(
    `/api/v1/venues/${encodeURIComponent(venueId)}/busyness${
      query ? `?${query}` : ""
    }`
  );

  return unwrapObject(payload, ["busyness", "snapshot", "data"]);
}

export async function getVenueBusynessForecast(venueId) {
  const payload = await apiRequest(
    `/api/v1/venues/${encodeURIComponent(venueId)}/busyness/forecast`
  );

  return unwrapObject(payload, ["forecast", "data"]);
}

export async function listReports({
  venueId,
  issueType,
  status = "active",
} = {}) {
  const params = new URLSearchParams();

  if (venueId) params.set("venue_id", venueId);
  if (issueType) params.set("issue_type", issueType);
  if (status) params.set("status", status);

  const query = params.toString();
  const payload = await apiRequest(
    `/api/v1/reports${query ? `?${query}` : ""}`
  );

  return unwrapArray(payload, ["reports", "items", "results", "data"]);
}

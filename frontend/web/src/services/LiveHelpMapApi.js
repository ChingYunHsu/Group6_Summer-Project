const DEFAULT_API_KEY = "development";

function getHeaders(extraHeaders = {}) {
  const headers = new Headers(extraHeaders);
  const apiKey =
    import.meta.env.VITE_API_KEY || DEFAULT_API_KEY;
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

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const message =
      payload?.message ||
      payload?.error ||
      payload?.detail ||
      (typeof payload === "string" && payload.trim()) ||
      `Request failed with status ${response.status}`;

    const requestError = new Error(message);
    requestError.status = response.status;
    requestError.payload = payload;
    throw requestError;
  }

  return payload;
}

function getCollection(payload, keys) {
  if (Array.isArray(payload)) {
    return payload;
  }

  for (const key of keys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }

  return [];
}

export async function listVenues(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => query.append(key, String(item)));
      return;
    }

    query.set(key, String(value));
  });

  const suffix = query.toString()
    ? `?${query.toString()}`
    : "";

  const payload = await apiRequest(
    `/api/v1/venues${suffix}`
  );

  return getCollection(payload, [
    "items",
    "venues",
    "data",
    "results",
  ]);
}

export async function getVenueById(venueId) {
  if (!venueId) {
    throw new Error("A venue ID is required.");
  }

  const payload = await apiRequest(
    `/api/v1/venues/${encodeURIComponent(venueId)}`
  );

  return payload?.venue ?? payload?.data ?? payload;
}

export async function getVenueBusyness(
  venueId,
  queryTime = ""
) {
  if (!venueId) {
    throw new Error("A venue ID is required.");
  }

  const query = new URLSearchParams();

  if (queryTime) {
    query.set("at", queryTime);
  }

  const suffix = query.toString()
    ? `?${query.toString()}`
    : "";

  return apiRequest(
    `/api/v1/venues/${encodeURIComponent(
      venueId
    )}/busyness${suffix}`
  );
}

export async function getVenueBusynessForecast(venueId) {
  if (!venueId) {
    throw new Error("A venue ID is required.");
  }

  return apiRequest(
    `/api/v1/venues/${encodeURIComponent(
      venueId
    )}/busyness/forecast`
  );
}

export async function listReports(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }

    query.set(key, String(value));
  });

  const suffix = query.toString()
    ? `?${query.toString()}`
    : "";

  const payload = await apiRequest(
    `/api/v1/reports${suffix}`
  );

  return getCollection(payload, [
    "items",
    "reports",
    "data",
    "results",
  ]);
}

export function getRouteOptions(
  destinationVenueId,
  origin
) {
  if (!destinationVenueId) {
    return Promise.reject(
      new Error("A destination venue ID is required.")
    );
  }

  if (
    !Number.isFinite(Number(origin?.lat)) ||
    !Number.isFinite(Number(origin?.lng))
  ) {
    return Promise.reject(
      new Error("Valid origin coordinates are required.")
    );
  }

  const query = new URLSearchParams({
    destination_venue_id: destinationVenueId,
    origin_lat: String(origin.lat),
    origin_lon: String(origin.lng),
  });

  return apiRequest(
    `/api/v1/routes/options?${query.toString()}`
  );
}

export function getRouteDetail(
  destinationVenueId,
  origin,
  mode = "walk"
) {
  if (!destinationVenueId) {
    return Promise.reject(
      new Error("A destination venue ID is required.")
    );
  }

  if (
    !Number.isFinite(Number(origin?.lat)) ||
    !Number.isFinite(Number(origin?.lng))
  ) {
    return Promise.reject(
      new Error("Valid origin coordinates are required.")
    );
  }

  const supportedModes = new Set([
    "walk",
    "transit",
    "drive",
  ]);

  const selectedMode = supportedModes.has(mode)
    ? mode
    : "walk";

  const query = new URLSearchParams({
    destination_venue_id: destinationVenueId,
    origin_lat: String(origin.lat),
    origin_lon: String(origin.lng),
    mode: selectedMode,
  });

  return apiRequest(
    `/api/v1/routes/detail?${query.toString()}`
  );
}

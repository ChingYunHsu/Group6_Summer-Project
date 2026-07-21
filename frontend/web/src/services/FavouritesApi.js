const DEFAULT_API_KEY = "development";

function buildHeaders(extraHeaders = {}) {
  const headers = new Headers(extraHeaders);

  const accessToken = localStorage.getItem("access_token");

  const apiKey =
    import.meta.env.VITE_API_KEY || DEFAULT_API_KEY;

  headers.set("Accept", "application/json");
  headers.set("X-Client-Origin", "web");

  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`
    );
  }

  return headers;
}

async function favouritesRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: buildHeaders(options.headers),
  });

  if (response.status === 204) {
    return null;
  }

  const payload = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    let fallbackMessage =
      `Request failed with status ${response.status}`;

    if (response.status === 400) {
      fallbackMessage =
        "The favourite request contained invalid information.";
    }

    if (response.status === 401) {
      fallbackMessage =
        "You must be signed in before managing saved locations.";
    }

    if (response.status === 403) {
      fallbackMessage =
        "This favourites action is not available from the web client.";
    }

    if (response.status === 404) {
      fallbackMessage =
        "The selected venue or favourite could not be found.";
    }

    if (response.status === 409) {
      fallbackMessage =
        "This location has already been added to your favourites.";
    }

    const message =
      payload?.message ||
      payload?.error ||
      payload?.detail ||
      fallbackMessage;

    throw new Error(message);
  }

  return payload;
}

function unwrapFavouriteList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  const possibleKeys = [
    "favourites",
    "favorites",
    "saved_venues",
    "items",
    "results",
    "data",
  ];

  for (const key of possibleKeys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }

  return [];
}

export async function listFavourites() {
  const payload = await favouritesRequest(
    "/api/v1/user/favourites"
  );

  return unwrapFavouriteList(payload);
}

export async function addFavourite(venueId) {
  if (!venueId) {
    throw new Error(
      "A venue ID is required to add a favourite."
    );
  }

  return favouritesRequest(
    "/api/v1/user/favourites",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        venue_id: venueId,
      }),
    }
  );
}

export async function deleteFavourite(venueId) {
  if (!venueId) {
    throw new Error(
      "A venue ID is required to remove a favourite."
    );
  }

  await favouritesRequest(
    `/api/v1/user/favourites/${encodeURIComponent(
      venueId
    )}`,
    {
      method: "DELETE",
    }
  );
}
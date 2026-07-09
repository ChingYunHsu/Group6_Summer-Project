import {
  BusynessResponse,
  ForecastResponse,
  Report,
  ReportResponse,
  RouteDetail,
  RouteOptionsResponse,
  Venue,
  VenueResponse,
} from "../types/venue";
import { ChatbotResponse } from "../types/chatbot";

import { getAccessToken } from "./tokenStorage";

/* -------------------------------------------------------------------------- */
/*                                  CONFIG                                    */
/* -------------------------------------------------------------------------- */

// Replace with backend URL.
// Examples:
//
// Android Emulator
// http://10.0.2.2:5000/api/v1
//
// iOS Simulator
// http://localhost:5000/api/v1
//
// Physical Device
// http://192.168.x.x:5000/api/v1

const API_BASE = "http://127.0.0.1:5000/api/v1";

// Some backend routes (venues, routes, realtime, and a handful of /user/*
// endpoints) check X-API-Key instead of/alongside the Bearer token — see
// require_api_key in backend/src/auth.py. Locally this is a no-op unless
// the backend's own API_KEY env var is set, but staging/prod will enforce
// it, so this needs to be sent unconditionally either way.
// Set EXPO_PUBLIC_API_KEY in your .env once the team assigns a real dev
// key; "development" is just a harmless placeholder until then.
const API_KEY = process.env.EXPO_PUBLIC_API_KEY ?? "development";

/* -------------------------------------------------------------------------- */
/*                               HTTP HELPER                                  */
/* -------------------------------------------------------------------------- */

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken();

  const response = await fetch(`${API_BASE}${endpoint}`, {
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

    let parsedBody: any = null;

    try {
      parsedBody = JSON.parse(text);
    } catch {
      // Not JSON — leave parsedBody null, fall back to raw text below.
    }

    const error = new Error(
      parsedBody?.error ?? `API ${response.status}: ${text}`,
    ) as Error & { status?: number; body?: any };

    error.status = response.status;
    error.body = parsedBody;

    throw error;
  }

  // Handle DELETE endpoints that return 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/* -------------------------------------------------------------------------- */
/*                                  VENUES                                    */
/* -------------------------------------------------------------------------- */

export async function getVenues(filters?: {
  languages?: string[];
  accessible?: boolean;
  open_now?: boolean;
}): Promise<Venue[]> {
  const params = new URLSearchParams();

  if (filters?.languages && filters.languages.length) {
    params.set("languages", filters.languages.join(","));
  }

  if (filters?.accessible !== undefined) {
    params.set("accessible", String(filters.accessible));
  }

  if (filters?.open_now !== undefined) {
    params.set("open_now", String(filters.open_now));
  }

  const query = params.toString().length ? `?${params.toString()}` : "";

  const data = await request<VenueResponse>(`/venues${query}`);

  return data.items;
}

export async function getVenue(venueId: string): Promise<Venue> {
  return request<Venue>(`/venues/${venueId}`);
}

/* -------------------------------------------------------------------------- */
/*                               BUSYNESS                                     */
/* -------------------------------------------------------------------------- */

export async function getVenueBusyness(
  venueId: string,
): Promise<BusynessResponse> {
  return request<BusynessResponse>(`/venues/${venueId}/busyness`);
}

export async function getVenueForecast(
  venueId: string,
): Promise<ForecastResponse> {
  return request<ForecastResponse>(`/venues/${venueId}/busyness/forecast`);
}

/* -------------------------------------------------------------------------- */
/*                                  REPORTS                                   */
/* -------------------------------------------------------------------------- */

export async function getReports(): Promise<Report[]> {
  const data = await request<ReportResponse>("/reports");

  return data.items;
}

export async function submitReport(payload: {
  venue_id?: string;

  issue_type: string;

  latitude: number;

  longitude: number;

  accuracy_meters?: number;

  description?: string;

  anonymous?: boolean;
}) {
  return request("/reports", {
    method: "POST",

    body: JSON.stringify(payload),
  });
}

export async function confirmReport(
  reportId: string,
  action:
    | "still_here"
    | "resolved"
    | "not_sure"
    | "still_out_of_order"
    | "open_now",
) {
  return request(`/reports/${reportId}/confirmations`, {
    method: "POST",

    body: JSON.stringify({
      action,
    }),
  });
}

/* -------------------------------------------------------------------------- */
/*                                  ROUTES                                    */
/* -------------------------------------------------------------------------- */

export async function getRouteOptions(): Promise<RouteOptionsResponse> {
  return request<RouteOptionsResponse>("/routes/options");
}

export async function getRouteDetail(): Promise<RouteDetail> {
  return request<RouteDetail>("/routes/detail");
}

/* -------------------------------------------------------------------------- */
/*                                 CHATBOT                                    */
/* -------------------------------------------------------------------------- */

// NOTE: as of this writing, ask_chatbot() on the backend is a static mock —
// it returns the same CHATBOT_RESPONSE regardless of `message` content, and
// does not call Gemini despite GEMINI_API_KEY existing in settings.py. This
// function is correctly wired to the real endpoint; the responses just
// aren't real yet.
export async function sendChatbotMessage(payload: {
  message: string;
  language?: string;
}): Promise<ChatbotResponse> {
  return request<ChatbotResponse>("/chatbot", {
    method: "POST",

    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------- */
/*                                   USER                                     */
/* -------------------------------------------------------------------------- */

// Note: delete_account() in user.py is decorated with require_api_key, not
// require_bearer_auth like most other /user/* routes — but request() sends
// both headers on every call regardless, so this works either way.
export async function deleteAccount(): Promise<{
  status: string;
  message: string;
  purge_deadline?: string;
}> {
  return request("/user/account", {
    method: "DELETE",
  });
}

/* -------------------------------------------------------------------------- */
/*                                FAVOURITES                                  */
/* -------------------------------------------------------------------------- */

// NOTE: as of this writing these three endpoints aren't actually per-user
// on the backend (see the comment on the Favourite type in types/venue.ts)
// — this client code is correct for the intended contract, but until the
// backend catches up, "favourites" behaves as one shared global list, and
// add_favourite always returns the same hardcoded favourite_id/saved_at
// regardless of what was added.

/* export async function getFavourites(): Promise<FavouritesResponse> {
  return request<FavouritesResponse>("/user/favourites");
}

export async function addFavourite(venueId: string): Promise<Favourite> {
  return request<Favourite>("/user/favourites", {
    method: "POST",

    body: JSON.stringify({ venue_id: venueId }),
  });
}

export async function removeFavourite(venueId: string): Promise<void> {
  return request<void>(`/user/favourites/${venueId}`, {
    method: "DELETE",
  });
} */

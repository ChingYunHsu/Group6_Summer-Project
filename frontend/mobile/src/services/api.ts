import { router } from "expo-router";
import { Alert, Platform } from "react-native";

// Plain i18next instance import, not react-i18next's useTranslation() hook —
// request() below is an ordinary function in a plain module, not a React
// component or another hook, so useTranslation() can't be called here at
// all (hooks only work inside component/hook call trees). i18next's own
// instance exposes t() as a plain function specifically for exactly this
// situation.
import i18n from "../i18n";

import {
  BusynessResponse,
  Favourite,
  FavouritesResponse,
  ForecastResponse,
  Report,
  ReportResponse,
  RouteDetail,
  RouteOptionsResponse,
  Venue,
  VenueResponse,
} from "../types/venue";
import { ChatbotResponse } from "../types/chatbot";
import { TranslateResponse } from "../types/translate";

import { clearAccessToken, getAccessToken } from "./tokenStorage";

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

// Android has its own special alias for
// "the host machine" instead: 10.0.2.2.
const API_HOST = Platform.OS === "android" ? "10.0.2.2" : "127.0.0.1";

const API_BASE = `http://${API_HOST}:5000/api/v1`;

// Some backend routes (venues, routes, realtime, and a handful of /user/*
// endpoints) check X-API-Key instead of/alongside the Bearer token — see
// require_api_key in backend/src/auth.py. Locally this is a no-op unless
// the backend's own API_KEY env var is set, but staging/prod will enforce
// it, so this needs to be sent unconditionally either way.
// Set EXPO_PUBLIC_API_KEY in your .env once the team assigns a real dev
// key; "development" is just a harmless placeholder until then.
const API_KEY = process.env.EXPO_PUBLIC_API_KEY ?? "development";

// Guards against showing the session-expired alert more than once when
// several requests 401 in the same moment (e.g. profile.tsx fetches
// profile + medical + favourites together on every focus).
let isHandlingSessionExpiry = false;

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

    const message = parsedBody?.error ?? `API ${response.status}: ${text}`;

    if (
      response.status === 401 &&
      message === "Unauthorized. Token expired." &&
      !isHandlingSessionExpiry
    ) {
      isHandlingSessionExpiry = true;

      await clearAccessToken();

      Alert.alert(
        i18n.t("api.sessionExpiredTitle", { defaultValue: "Session expired" }),
        i18n.t("api.sessionExpiredMessage", {
          defaultValue: "Please log in again to continue.",
        }),
        [
          {
            text: i18n.t("api.sessionExpiredConfirm", { defaultValue: "OK" }),
            onPress: () => {
              router.replace("/auth-gateway");
              isHandlingSessionExpiry = false;
            },
          },
        ],
      );
    }

    const error = new Error(message) as Error & {
      status?: number;
      body?: any;
    };

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

export async function getRouteOptions(
  destinationVenueId: string | undefined,
  origin: { latitude: number; longitude: number },
): Promise<RouteOptionsResponse> {
  const params = new URLSearchParams();

  if (destinationVenueId) {
    params.set("destination_venue_id", destinationVenueId);
  }

  params.set("origin_lat", String(origin.latitude));
  params.set("origin_lon", String(origin.longitude));

  return request<RouteOptionsResponse>(`/routes/options?${params.toString()}`);
}

export async function getRouteDetail(
  destinationVenueId: string | undefined,
  origin: { latitude: number; longitude: number },
  mode: string,
): Promise<RouteDetail> {
  const params = new URLSearchParams();

  if (destinationVenueId) {
    params.set("destination_venue_id", destinationVenueId);
  }

  params.set("origin_lat", String(origin.latitude));
  params.set("origin_lon", String(origin.longitude));
  params.set("mode", mode);

  return request<RouteDetail>(`/routes/detail?${params.toString()}`);
}

/* -------------------------------------------------------------------------- */
/*                                 CHATBOT                                    */
/* -------------------------------------------------------------------------- */

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

export async function getFavourites(): Promise<FavouritesResponse> {
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
}

/* -------------------------------------------------------------------------- */
/*                                TRANSLATE                                   */
/* -------------------------------------------------------------------------- */

// require_bearer_auth server-side (confirmed via test_translate_requires_
// bearer_token) — a guest with no token gets a real 401 here, same as any
// other auth-gated endpoint. show-staff.tsx distinguishes that specific
// case from a genuine translation failure (Gemini down, etc.) so it can
// show "log in to use this" rather than a generic error message.
export async function translateText(
  text: string,
  sourceLanguage: string,
  targetLanguage: string,
): Promise<TranslateResponse> {
  return request<TranslateResponse>("/translate", {
    method: "POST",

    body: JSON.stringify({
      text,
      sourceLanguage,
      targetLanguage,
    }),
  });
}

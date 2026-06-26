import {
  BusynessResponse,
  ForecastResponse,
  Report,
  ReportResponse,
  RouteOptionsResponse,
  Venue,
  VenueResponse,
} from "../types/venue";

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

// Until implementation of real API keys this can stay as a placeholder.
const API_KEY = "development";

/* -------------------------------------------------------------------------- */
/*                               HTTP HELPER                                  */
/* -------------------------------------------------------------------------- */

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(
    `${API_BASE}${endpoint}`,
    {
      ...options,

      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        ...(options.headers ?? {}),
      },
    }
  );

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `API ${response.status}: ${text}`
    );
  }

  return response.json();
}

/* -------------------------------------------------------------------------- */
/*                                  VENUES                                    */
/* -------------------------------------------------------------------------- */

export async function getVenues(
  filters?: {
    languages?: string[];
    accessible?: boolean;
    open_now?: boolean;
  }
): Promise<Venue[]> {
  const params =
    new URLSearchParams();

  if (
    filters?.languages &&
    filters.languages.length
  ) {
    params.set(
      "languages",
      filters.languages.join(",")
    );
  }

  if (
    filters?.accessible !==
    undefined
  ) {
    params.set(
      "accessible",
      String(filters.accessible)
    );
  }

  if (
    filters?.open_now !==
    undefined
  ) {
    params.set(
      "open_now",
      String(filters.open_now)
    );
  }

  const query =
    params.toString().length
      ? `?${params.toString()}`
      : "";

  const data =
    await request<VenueResponse>(
      `/venues${query}`
    );

  return data.items;
}

export async function getVenue(
  venueId: string
): Promise<Venue> {
  return request<Venue>(
    `/venues/${venueId}`
  );
}

/* -------------------------------------------------------------------------- */
/*                               BUSYNESS                                     */
/* -------------------------------------------------------------------------- */

export async function getVenueBusyness(
  venueId: string
): Promise<BusynessResponse> {
  return request<BusynessResponse>(
    `/venues/${venueId}/busyness`
  );
}

export async function getVenueForecast(
  venueId: string
): Promise<ForecastResponse> {
  return request<ForecastResponse>(
    `/venues/${venueId}/busyness/forecast`
  );
}

/* -------------------------------------------------------------------------- */
/*                                  REPORTS                                   */
/* -------------------------------------------------------------------------- */

export async function getReports(): Promise<
  Report[]
> {
  const data =
    await request<ReportResponse>(
      "/reports"
    );

  return data.items;
}

export async function submitReport(
  payload: {
    venue_id?: string;

    issue_type: string;

    latitude: number;

    longitude: number;

    description?: string;

    anonymous?: boolean;
  }
) {
  return request(
    "/reports",
    {
      method: "POST",

      body: JSON.stringify(
        payload
      ),
    }
  );
}

export async function confirmReport(
  reportId: string,
  action:
    | "still_here"
    | "resolved"
    | "not_sure"
    | "still_out_of_order"
    | "open_now"
) {
  return request(
    `/reports/${reportId}/confirmations`,
    {
      method: "POST",

      body: JSON.stringify({
        action,
      }),
    }
  );
}

/* -------------------------------------------------------------------------- */
/*                                  ROUTES                                    */
/* -------------------------------------------------------------------------- */

export async function getRouteOptions(): Promise<RouteOptionsResponse> {
  return request<RouteOptionsResponse>(
    "/routes/options"
  );
}

export async function getRouteDetail() {
  return request(
    "/routes/detail"
  );
}
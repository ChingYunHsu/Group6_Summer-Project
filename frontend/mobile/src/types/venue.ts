/* -------------------------------------------------------------------------- */
/*                              VENUE TYPES                                   */
/* -------------------------------------------------------------------------- */

export type VenueCategory =
  | "clinic"
  | "pharmacy"
  | "emergencyasset"
  | "hospital"
  | "restroom"
  | "healthcare"
  | "dentist"
  | "laboratory";

export interface VenueBusyness {
  busyness_score: number;
  busyness_status: string;
  busyness_color: string;
  estimated_wait_minutes: number;
  updated_at?: string;
  data_mode?: "forecast" | "unavailable";
  forecast_source?: string;
  unavailable_reason?: string;
}

export interface VenueAccessibility {
  wheelchair_friendly: boolean;
  step_free_route: boolean;
  accessible_toilet: boolean;
  entrance_width_cm: number;
}

export interface VenueLanguage {
  language_tag: string[];
  support_level: string;
  chatbot_enabled: boolean;
  chatbot_welcoming_message: string;
}

export interface VenueWarning {
  active_warning: boolean;
  warning_detail: string;
  wait_alert: boolean;

  replacement_suggestion?: {
    venue_id: string;
    venue_name: string;
    reason: string;
  } | null;
}

export interface VenueForecast {
  offset_hours: number;

  percent: number;

  level: string;
}

export interface Venue {
  venue_id: string;

  name: string;

  venue_type: VenueCategory;

  latitude: number;

  longitude: number;

  borough: string;

  address: string;

  phone: string;

  opening_hours: string;

  rating: number;

  language_tags: string[];

  accessibility?: VenueAccessibility;

  language?: VenueLanguage;

  warnings?: VenueWarning;

  busyness?: VenueBusyness;

  accessible_status: string;

  accessibility_features: string[];

  active_warning: boolean;

  live_report_count: number;

  distance_km: number;

  open_now: boolean;

  busyness_level: string;

  busyness_percent: number;

  avg_wait_minutes: number;

  supported_services: string[];

  live_status_badge: string;

  // Also mock-only — see note above.
  busyness_forecast_12h?: VenueForecast[];

  forecast_mode: string;

  is_favourite: boolean;

  source: string;

  data_confidence: number;

  created_at: string;
}

export interface VenueResponse {
  count: number;

  items: Venue[];
}

/* -------------------------------------------------------------------------- */
/*                               REPORT TYPES                                 */
/* -------------------------------------------------------------------------- */

export interface ReportConfirmation {
  count: number;

  latest_action: string;

  latest_action_at: string;
}

export interface Report {
  report_id: string;

  venue_id?: string;

  issue_type: string;

  issue_type_label: string;

  report_scope: "venue_bound" | "standalone";

  status: string;

  latitude: number;

  longitude: number;

  created_at: string;

  expires_at: string | null;

  confirmations: ReportConfirmation;

  venue_name?: string;

  venue_category?: string;

  accuracy_meters?: number;

  anonymous?: boolean;

  description?: string;

  photos?: string[];

  expires_in_minutes?: number;

  badge_text?: string;

  live_report_count?: number;
}

export interface ReportResponse {
  count: number;

  items: Report[];
}

/* -------------------------------------------------------------------------- */
/*                               FAVOURITES                                   */
/* -------------------------------------------------------------------------- */

export interface Favourite {
  favourite_id: string;

  venue_id: string;

  saved_at: string;

  display_status: string;
}

export interface FavouritesResponse {
  count: number;

  items: Favourite[];
}

/* -------------------------------------------------------------------------- */
/*                              ROUTE TYPES                                   */
/* -------------------------------------------------------------------------- */

export interface RouteOption {
  mode: string;

  duration_minutes: number;

  accessibility_mode: string;

  status: string;

  summary: string;
}

export interface RouteOptionsResponse {
  origin_label: string;

  destination_venue_id: string;

  departure_time_label: string;

  summary_by_mode: Record<string, any>;

  options: RouteOption[];
}

export interface RouteDetail {
  destination_venue_id?: string;

  polyline_preview?: { latitude: number; longitude: number }[];

  steps: string[];

  start_navigation_label?: string;
}

/* -------------------------------------------------------------------------- */
/*                             BUSYNESS TYPES                                 */
/* -------------------------------------------------------------------------- */

export interface BusynessResponse {
  venue_id: string;

  busyness: VenueBusyness;
}

export interface ForecastResponse {
  venue_id: string;

  data_mode: "forecast" | "unavailable";
  forecast_source: string;
  unavailable_reason?: string;

  forecast: VenueForecast[];

  // Absent on an unavailable response — there's no "best time" when
  // there's no real data to rank.
  best_time_to_go_today?: {
    offset_hours: number;
    percent: number;
    label: string;
  };
}

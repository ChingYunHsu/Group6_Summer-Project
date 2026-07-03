/* -------------------------------------------------------------------------- */
/*                              VENUE TYPES                                   */
/* -------------------------------------------------------------------------- */

export type VenueCategory =
  | "clinic"
  | "pharmacy"
  | "emergencyasset";

export interface VenueBusyness {
  busyness_score: number;
  busyness_status: string;
  busyness_color: string;
  estimated_wait_minutes: number;
  updated_at?: string;
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

  accessibility: VenueAccessibility;

  language: VenueLanguage;

  warnings: VenueWarning;

  accessible_status: string;

  accessibility_features: string[];

  active_warning: boolean;

  live_report_count: number;

  distance_km: number;

  open_now: boolean;

  busyness: VenueBusyness;

  busyness_level: string;

  busyness_percent: number;

  avg_wait_minutes: number;

  supported_services: string[];

  live_status_badge: string;

  busyness_forecast_12h: VenueForecast[];

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

  venue_name?: string;

  venue_category?: string;

  issue_type: string;

  latitude: number;

  longitude: number;

  accuracy_m: number;

  anonymous: boolean;

  description: string;

  photos: string[];

  status: string;

  created_at: string;

  expires_at: string;

  expires_in_minutes: number;

  confirmations: ReportConfirmation;

  badge_text: string;

}

export interface ReportResponse {

  count: number;

  items: Report[];

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
  duration: number;
  steps: string[];
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

  forecast: VenueForecast[];

  best_time_to_go_today: {

    offset_hours: number;

    percent: number;

    label: string;

  };

}
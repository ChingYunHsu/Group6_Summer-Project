import {
  render,
  screen,
  waitFor,
  cleanup,
} from "@testing-library/react-native";

import VenueBottomSheet from "../../components/VenueBottomSheet";
import { getVenueBusyness, getVenueForecast } from "../../services/api";
import { ForecastResponse, Venue } from "../../types/venue";

jest.mock("react-native-maps", () => {
  const { View } = require("react-native");

  const MockMapView = ({ children, ...props }: any) => (
    <View {...props}>{children}</View>
  );
  const MockMarker = ({ children, ...props }: any) => (
    <View {...props}>{children}</View>
  );
  const MockCallout = ({ children, ...props }: any) => (
    <View {...props}>{children}</View>
  );
  const MockPolyline = (props: any) => <View {...props} />;

  return {
    __esModule: true,
    default: MockMapView,
    Marker: MockMarker,
    Callout: MockCallout,
    Polyline: MockPolyline,
  };
});

jest.mock("../../services/api", () => ({
  getVenueBusyness: jest.fn(),
  getVenueForecast: jest.fn(),
}));

const mockGetVenueBusyness = getVenueBusyness as jest.MockedFunction<
  typeof getVenueBusyness
>;
const mockGetVenueForecast = getVenueForecast as jest.MockedFunction<
  typeof getVenueForecast
>;

// Full, valid Venue fixture — every required field on the real interface
// filled with a plausible value, so each test only needs to override the
// one or two fields it actually cares about (venue_type, mainly).
function buildVenue(overrides: Partial<Venue> = {}): Venue {
  return {
    venue_id: "v_test_1",
    name: "Test Venue",
    venue_type: "clinic",
    latitude: 40.758,
    longitude: -73.9855,
    borough: "Manhattan",
    address: "123 Test Ave, New York, NY",
    phone: "+1 212 555 0100",
    opening_hours: "9am-5pm",
    rating: 4.5,
    language_tags: ["EN"],
    accessible_status: "full_access",
    accessibility_features: [],
    active_warning: false,
    live_report_count: 0,
    distance_km: 0.5,
    open_now: true,
    busyness_level: "quiet",
    busyness_percent: 20,
    avg_wait_minutes: 5,
    supported_services: [],
    live_status_badge: "",
    forecast_mode: "",
    is_favourite: false,
    source: "db",
    data_confidence: 1,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

// No live-status badge in any of these four cases — every scenario here
// is specifically about the /busyness/forecast (chart) response. Kept
// as "unavailable" across the board so the badge assertion stays
// consistent and isn't a variable each test has to separately account
// for.
const unavailableBusyness = {
  venue_id: "v_test_1",
  busyness: {
    busyness_score: 0,
    busyness_status: "",
    busyness_color: "",
    estimated_wait_minutes: 0,
    data_mode: "unavailable" as const,
  },
};

describe("VenueBottomSheet — Sprint 5 V2 data_mode gating", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetVenueBusyness.mockResolvedValue(unavailableBusyness);
  });

  afterEach(() => {
    cleanup();
  });

  // ---------------------------------------------------------------------
  // Case 1: AED and restroom fixtures render "• No Live Info"
  // ---------------------------------------------------------------------

  it("renders '• No Live Info' for an AED (emergencyasset) venue", async () => {
    const aedForecast: ForecastResponse = {
      venue_id: "v_test_1",
      data_mode: "unavailable",
      forecast_source: "busyness_forecasts",
      unavailable_reason: "ineligible_venue_type",
      forecast: [],
    };
    mockGetVenueForecast.mockResolvedValue(aedForecast);

    render(
      <VenueBottomSheet
        visible
        venue={buildVenue({ venue_type: "emergencyasset" })}
        autoCurrentTime
        onClose={jest.fn()}
        onDirectionsPress={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("• No Live Info")).toBeTruthy();
    });

    expect(screen.queryByText(/12-Hour Busyness Forecast/i)).toBeNull();
  });

  it("renders '• No Live Info' for a restroom venue", async () => {
    const restroomForecast: ForecastResponse = {
      venue_id: "v_test_1",
      data_mode: "unavailable",
      forecast_source: "busyness_forecasts",
      unavailable_reason: "ineligible_venue_type",
      forecast: [],
    };
    mockGetVenueForecast.mockResolvedValue(restroomForecast);

    render(
      <VenueBottomSheet
        visible
        venue={buildVenue({ venue_type: "restroom" })}
        autoCurrentTime
        onClose={jest.fn()}
        onDirectionsPress={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("• No Live Info")).toBeTruthy();
    });

    expect(screen.queryByText(/12-Hour Busyness Forecast/i)).toBeNull();
  });

  // ---------------------------------------------------------------------
  // Case 2: eligible type + real V2 data renders the 12-hour chart
  // ---------------------------------------------------------------------

  it("renders the 12-hour forecast chart for a clinic with V2 data", async () => {
    const clinicForecast: ForecastResponse = {
      venue_id: "v_test_1",
      data_mode: "forecast",
      forecast_source: "busyness_forecasts",
      forecast: Array.from({ length: 12 }, (_, i) => ({
        offset_hours: i,
        percent: 30 + i,
        level: "moderate",
      })),
      best_time_to_go_today: {
        offset_hours: 3,
        percent: 15,
        label: "In 3 hours",
      },
    };
    mockGetVenueForecast.mockResolvedValue(clinicForecast);

    render(
      <VenueBottomSheet
        visible
        venue={buildVenue({ venue_type: "clinic" })}
        autoCurrentTime
        onClose={jest.fn()}
        onDirectionsPress={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/12-Hour Busyness Forecast/i)).toBeTruthy();
    });

    expect(screen.queryByText("• No Live Info")).toBeNull();
  });

  // ---------------------------------------------------------------------
  // Case 3: eligible type, but no V2 rows yet — unavailable, not a crash
  // ---------------------------------------------------------------------

  it("renders '• No Live Info' for an eligible venue with an empty forecast", async () => {
    const emptyForecast: ForecastResponse = {
      venue_id: "v_test_1",
      data_mode: "unavailable",
      forecast_source: "busyness_forecasts",
      unavailable_reason: "no_v2_forecast",
      forecast: [],
    };
    mockGetVenueForecast.mockResolvedValue(emptyForecast);

    render(
      <VenueBottomSheet
        visible
        venue={buildVenue({ venue_type: "hospital" })}
        autoCurrentTime
        onClose={jest.fn()}
        onDirectionsPress={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("• No Live Info")).toBeTruthy();
    });

    expect(screen.queryByText(/12-Hour Busyness Forecast/i)).toBeNull();
  });

  // ---------------------------------------------------------------------
  // Case 4: a legacy/mock-shaped payload must never render as a forecast
  // ---------------------------------------------------------------------

  it("never renders a chart for a legacy-shaped payload with no data_mode", async () => {
    const legacyShapedPayload = {
      venue_id: "v_test_1",
      forecast: [{ offset_hours: 0, percent: 30, level: "quiet" }],
      // No data_mode field at all — mirrors today's pre-Sprint-5 backend
      // response shape.
    } as unknown as ForecastResponse;

    mockGetVenueForecast.mockResolvedValue(legacyShapedPayload);

    render(
      <VenueBottomSheet
        visible
        venue={buildVenue({ venue_type: "clinic" })}
        autoCurrentTime
        onClose={jest.fn()}
        onDirectionsPress={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("• No Live Info")).toBeTruthy();
    });

    expect(screen.queryByText(/12-Hour Busyness Forecast/i)).toBeNull();
  });
});

import { fireEvent, render, waitFor } from "@testing-library/react-native";

import MapScreen from "../(tabs)/map";
import {
  confirmReport,
  getFavourites,
  getReports,
  getVenueBusyness,
  getVenues,
} from "../../services/api";
import { getAccessToken } from "../../services/authService";

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

  return {
    __esModule: true,
    default: MockMapView,
    Marker: MockMarker,
    Callout: MockCallout,
  };
});

jest.mock("expo-location", () => ({
  hasServicesEnabledAsync: jest.fn().mockResolvedValue(true),
  requestForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: { latitude: 40.75, longitude: -73.98 },
  }),
  getForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
  Accuracy: { Balanced: 3 },
}));

jest.mock("expo-router", () => ({
  router: { push: jest.fn(), back: jest.fn(), replace: jest.fn() },
}));

jest.mock("../../services/authService", () => ({
  getAccessToken: jest.fn(),
}));

jest.mock("../../services/api", () => ({
  getVenues: jest.fn(),
  getReports: jest.fn(),
  getFavourites: jest.fn(),
  getVenueBusyness: jest.fn(),
  confirmReport: jest.fn(),
  submitReport: jest.fn(),
  getRouteOptions: jest.fn(),
  getRouteDetail: jest.fn(),
}));

jest.mock("../../components/CategoryChips", () => () => null);
jest.mock("../../components/FloatingActionButtons", () => () => null);
jest.mock("../../components/LocationRequiredModal", () => () => null);
jest.mock("../../components/MapSearchBar", () => () => null);
jest.mock("../../components/ReportModal", () => () => null);
jest.mock("../../components/RouteDetailModal", () => () => null);
jest.mock("../../components/RouteOptionsModal", () => () => null);
jest.mock("../../components/VenueBottomSheet", () => () => null);

jest.mock("../../components/VenueMarker", () => {
  const { Pressable, Text } = require("react-native");

  return function MockVenueMarker({ venue, onPress }: any) {
    return (
      <Pressable
        testID={`venue-marker-${venue.venue_id}`}
        onPress={() => onPress(venue)}
      >
        <Text>{venue.name}</Text>
      </Pressable>
    );
  };
});

jest.mock("../../components/FilterModal", () => {
  const { View, Button } = require("react-native");

  return function MockFilterModal({ onApply }: any) {
    const baseFilters = {
      openNow: undefined,
      language: "",
      autoCurrentTime: true,
      date: "Today",
      time: "Now",
      timeOffset: 0,
    };

    return (
      <View>
        <Button
          title="Apply: Full Wheelchair Access"
          onPress={() =>
            onApply({
              ...baseFilters,
              wheelchairAccess: "full_access",
              liveStatus: undefined,
            })
          }
        />
        <Button
          title="Apply: Partial or Full Wheelchair Access"
          onPress={() =>
            onApply({
              ...baseFilters,
              wheelchairAccess: "partial_or_full",
              liveStatus: undefined,
            })
          }
        />
        <Button
          title="Apply: Busy"
          onPress={() =>
            onApply({
              ...baseFilters,
              wheelchairAccess: undefined,
              liveStatus: "busy",
            })
          }
        />
        <Button
          title="Apply: No Filters"
          onPress={() =>
            onApply({
              ...baseFilters,
              wheelchairAccess: undefined,
              liveStatus: undefined,
            })
          }
        />
      </View>
    );
  };
});

jest.mock("../../components/ReportMarker", () => {
  const { Pressable, Text } = require("react-native");

  return function MockReportMarker({ report, onPress }: any) {
    return (
      <Pressable
        testID={`report-marker-${report.report_id}`}
        onPress={() => onPress(report)}
      >
        <Text>Report Marker</Text>
      </Pressable>
    );
  };
});
jest.mock("../../components/ReportBottomSheet", () => {
  const { View, Button } = require("react-native");

  return function MockReportBottomSheet({
    visible,
    report,
    onConfirm,
    onResolve,
  }: any) {
    if (!visible || !report) return null;

    return (
      <View>
        <Button title="Confirm" onPress={() => onConfirm(report.report_id)} />
        <Button title="Resolve" onPress={() => onResolve(report.report_id)} />
      </View>
    );
  };
});

jest.mock("../../components/LoginRequiredModal", () => {
  const { Text } = require("react-native");

  return function MockLoginRequiredModal({ visible }: { visible: boolean }) {
    if (!visible) return null;
    return <Text testID="login-required-modal">LOGIN_REQUIRED</Text>;
  };
});

/* -------------------------------------------------------------------------- */
/*                                  FIXTURES                                  */
/* -------------------------------------------------------------------------- */

const mockActiveReport = {
  report_id: "r_9001",
  venue_id: "v_1001",
  issue_type: "elevator_broken",
  issue_type_label: "Lift Broken",
  report_scope: "venue_bound" as const,
  status: "active",
  latitude: 40.75,
  longitude: -73.98,
  created_at: new Date().toISOString(),
  expires_at: null,
  confirmations: {
    count: 2,
    latest_action: "still_here",
    latest_action_at: new Date().toISOString(),
  },
};

// All venue_type: "clinic" — matching map.tsx's default category state,
// so every fixture below is included in filteredVenues before any
// wheelchair/live-status filter narrows it down. CategoryChips is mocked
// away, so category never actually changes from its default in this file.
const mockVenueFullAccess = {
  venue_id: "v_full",
  name: "Full Access Clinic",
  venue_type: "clinic",
  latitude: "40.75",
  longitude: "-73.98",
  accessible_status: "full_access",
  address: "1 Test St",
  active_warning: 0,
};

const mockVenuePartialAccess = {
  venue_id: "v_partial",
  name: "Partial Access Clinic",
  venue_type: "clinic",
  latitude: "40.75",
  longitude: "-73.98",
  accessible_status: "partial",
  address: "2 Test St",
  active_warning: 0,
};

const mockVenueUnknownAccess = {
  venue_id: "v_unknown",
  name: "Unknown Access Clinic",
  venue_type: "clinic",
  latitude: "40.75",
  longitude: "-73.98",
  accessible_status: "none",
  address: "3 Test St",
  active_warning: 0,
};

/* -------------------------------------------------------------------------- */
/*                                   TESTS                                    */
/* -------------------------------------------------------------------------- */

const mockedGetAccessToken = getAccessToken as jest.Mock;
const mockedGetVenues = getVenues as jest.Mock;
const mockedGetReports = getReports as jest.Mock;
const mockedGetFavourites = getFavourites as jest.Mock;
const mockedGetVenueBusyness = getVenueBusyness as jest.Mock;
const mockedConfirmReport = confirmReport as jest.Mock;

describe("MapScreen — Guest Mode report verification gating", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGetVenues.mockResolvedValue([]);
    mockedGetFavourites.mockResolvedValue({
      items: [],
    });
    mockedGetReports.mockResolvedValue([mockActiveReport]);
  });

  it("blocks a guest from confirming a report: shows LoginRequiredModal instead of calling the API", async () => {
    mockedGetAccessToken.mockResolvedValue(null); // no token = guest

    const screen = await render(<MapScreen />);

    fireEvent.press(await screen.findByTestId("report-marker-r_9001"));

    const confirmButton = await screen.findByText("Confirm");

    expect(screen.queryByTestId("login-required-modal")).toBeNull();

    fireEvent.press(confirmButton);

    expect(await screen.findByTestId("login-required-modal")).toBeTruthy();

    expect(mockedConfirmReport).not.toHaveBeenCalled();
  });

  it("blocks a guest from resolving a report the same way", async () => {
    mockedGetAccessToken.mockResolvedValue(null);

    const screen = await render(<MapScreen />);

    fireEvent.press(await screen.findByTestId("report-marker-r_9001"));

    const resolveButton = await screen.findByText("Resolve");

    fireEvent.press(resolveButton);

    expect(await screen.findByTestId("login-required-modal")).toBeTruthy();

    expect(mockedConfirmReport).not.toHaveBeenCalled();
  });

  it("lets an authenticated user confirm a report without LoginRequiredModal appearing", async () => {
    mockedGetAccessToken.mockResolvedValue("fake-access-token");

    const screen = await render(<MapScreen />);

    fireEvent.press(await screen.findByTestId("report-marker-r_9001"));

    const confirmButton = await screen.findByText("Confirm");

    fireEvent.press(confirmButton);

    await waitFor(() => {
      expect(mockedConfirmReport).toHaveBeenCalledWith("r_9001", "still_here");
    });

    expect(screen.queryByTestId("login-required-modal")).toBeNull();
  });

  it("lets an authenticated user resolve a report without LoginRequiredModal appearing", async () => {
    mockedGetAccessToken.mockResolvedValue("fake-access-token");

    const screen = await render(<MapScreen />);

    fireEvent.press(await screen.findByTestId("report-marker-r_9001"));

    const resolveButton = await screen.findByText("Resolve");

    fireEvent.press(resolveButton);

    await waitFor(() => {
      expect(mockedConfirmReport).toHaveBeenCalledWith("r_9001", "resolved");
    });

    expect(screen.queryByTestId("login-required-modal")).toBeNull();
  });
});

describe("MapScreen — Wheelchair access filtering", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGetAccessToken.mockResolvedValue(null);
    mockedGetFavourites.mockResolvedValue({ items: [] });
    mockedGetReports.mockResolvedValue([]);
    mockedGetVenues.mockResolvedValue([
      mockVenueFullAccess,
      mockVenuePartialAccess,
      mockVenueUnknownAccess,
    ]);
    mockedGetVenueBusyness.mockRejectedValue(new Error("not relevant here"));
  });

  it("shows all three venues before any wheelchair filter is applied", async () => {
    const screen = await render(<MapScreen />);

    expect(await screen.findByTestId("venue-marker-v_full")).toBeTruthy();
    expect(screen.getByTestId("venue-marker-v_partial")).toBeTruthy();
    expect(screen.getByTestId("venue-marker-v_unknown")).toBeTruthy();
  });

  it("Full Access filter shows only the confirmed-full-access venue", async () => {
    const screen = await render(<MapScreen />);

    await screen.findByTestId("venue-marker-v_full");

    fireEvent.press(screen.getByText("Apply: Full Wheelchair Access"));

    await waitFor(() => {
      expect(screen.queryByTestId("venue-marker-v_partial")).toBeNull();
    });

    expect(screen.getByTestId("venue-marker-v_full")).toBeTruthy();
    expect(screen.queryByTestId("venue-marker-v_unknown")).toBeNull();
  });

  it("Partial or Full Access filter shows both the partial and full venues, excluding unknown", async () => {
    const screen = await render(<MapScreen />);

    await screen.findByTestId("venue-marker-v_full");

    fireEvent.press(
      screen.getByText("Apply: Partial or Full Wheelchair Access"),
    );

    await waitFor(() => {
      expect(screen.queryByTestId("venue-marker-v_unknown")).toBeNull();
    });

    expect(screen.getByTestId("venue-marker-v_full")).toBeTruthy();
    expect(screen.getByTestId("venue-marker-v_partial")).toBeTruthy();
  });

  it("clearing the filter (re-selecting the same option) shows all venues again", async () => {
    const screen = await render(<MapScreen />);

    await screen.findByTestId("venue-marker-v_full");

    fireEvent.press(screen.getByText("Apply: Full Wheelchair Access"));

    await waitFor(() => {
      expect(screen.queryByTestId("venue-marker-v_unknown")).toBeNull();
    });

    fireEvent.press(screen.getByText("Apply: No Filters"));

    await waitFor(() => {
      expect(screen.getByTestId("venue-marker-v_unknown")).toBeTruthy();
    });

    expect(screen.getByTestId("venue-marker-v_full")).toBeTruthy();
    expect(screen.getByTestId("venue-marker-v_partial")).toBeTruthy();
  });
});

describe("MapScreen — Live status filtering", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGetAccessToken.mockResolvedValue(null);
    mockedGetFavourites.mockResolvedValue({ items: [] });
    mockedGetReports.mockResolvedValue([]);
    mockedGetVenues.mockResolvedValue([
      mockVenueFullAccess,
      mockVenuePartialAccess,
    ]);

    // Real, distinct busyness per venue_id — matching how the actual
    // effect calls getVenueBusyness once per venue, individually.
    mockedGetVenueBusyness.mockImplementation((venueId: string) => {
      if (venueId === "v_full") {
        return Promise.resolve({
          venue_id: venueId,
          busyness: {
            busyness_score: 90,
            busyness_status: "busy",
            busyness_color: "red",
            estimated_wait_minutes: 25,
          },
        });
      }
      return Promise.resolve({
        venue_id: venueId,
        busyness: {
          busyness_score: 20,
          busyness_status: "quiet",
          busyness_color: "green",
          estimated_wait_minutes: 2,
        },
      });
    });
  });

  it("Busy filter only shows the venue whose real busyness status is busy", async () => {
    const screen = await render(<MapScreen />);

    // Both markers exist before filtering — waiting specifically for
    // this confirms the busyness fetch has actually resolved for both
    // venues before the filter is applied, since the filter logic
    // deliberately excludes venues whose busyness hasn't loaded yet.
    await screen.findByTestId("venue-marker-v_full");
    await screen.findByTestId("venue-marker-v_partial");

    await waitFor(() => {
      expect(mockedGetVenueBusyness).toHaveBeenCalledWith("v_full");
      expect(mockedGetVenueBusyness).toHaveBeenCalledWith("v_partial");
    });

    fireEvent.press(screen.getByText("Apply: Busy"));

    await waitFor(() => {
      expect(screen.queryByTestId("venue-marker-v_partial")).toBeNull();
    });

    expect(screen.getByTestId("venue-marker-v_full")).toBeTruthy();
  });
});

import { fireEvent, render, waitFor } from "@testing-library/react-native";

import MapScreen from "../(tabs)/map";
import {
  confirmReport,
  getFavourites,
  getReports,
  getVenues,
} from "../../services/api";
import { getAccessToken } from "../../services/authService";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// This file is deliberately narrow: it only exercises MapScreen's
// report-confirmation guest-gating path (handleReportConfirmation). Every
// sibling overlay map.tsx renders is stubbed to () => null except
// ReportMarker (the actual UI under test, reached via its real Confirm/
// Resolve buttons) and LoginRequiredModal, which is replaced with a
// controlled stub — see the comment on that mock for why.

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
  confirmReport: jest.fn(),
  submitReport: jest.fn(),
  getRouteOptions: jest.fn(),
  getRouteDetail: jest.fn(),
}));

jest.mock("../../components/CategoryChips", () => () => null);
jest.mock("../../components/FilterModal", () => () => null);
jest.mock("../../components/FloatingActionButtons", () => () => null);
jest.mock("../../components/LocationRequiredModal", () => () => null);
jest.mock("../../components/MapSearchBar", () => () => null);
jest.mock("../../components/ReportModal", () => () => null);
jest.mock("../../components/RouteDetailModal", () => () => null);
jest.mock("../../components/RouteOptionsModal", () => () => null);
jest.mock("../../components/VenueBottomSheet", () => () => null);

// LoginRequiredModal's visibility is the thing under test, so it's mocked
// as a controlled stub that reflects the `visible` prop directly (renders
// nothing when false, a queryable Text when true) rather than relying on
// how React Native's real Modal component behaves inside this project's
// specific test renderer — that's an implementation detail this file
// shouldn't need to know about to verify map.tsx's gating logic.
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

const mockedGetAccessToken = getAccessToken as jest.Mock;
const mockedGetVenues = getVenues as jest.Mock;
const mockedGetReports = getReports as jest.Mock;
const mockedGetFavourites = getFavourites as jest.Mock;
const mockedConfirmReport = confirmReport as jest.Mock;

/* -------------------------------------------------------------------------- */
/*                                   TESTS                                    */
/* -------------------------------------------------------------------------- */

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

    const confirmButton = await screen.findByText("Confirm");

    expect(screen.queryByTestId("login-required-modal")).toBeNull();

    fireEvent.press(confirmButton);

    expect(await screen.findByTestId("login-required-modal")).toBeTruthy();

    expect(mockedConfirmReport).not.toHaveBeenCalled();
  });

  it("blocks a guest from resolving a report the same way", async () => {
    mockedGetAccessToken.mockResolvedValue(null);

    const screen = await render(<MapScreen />);

    const resolveButton = await screen.findByText("Resolve");

    fireEvent.press(resolveButton);

    expect(await screen.findByTestId("login-required-modal")).toBeTruthy();

    expect(mockedConfirmReport).not.toHaveBeenCalled();
  });

  it("lets an authenticated user confirm a report without LoginRequiredModal appearing", async () => {
    mockedGetAccessToken.mockResolvedValue("fake-access-token");

    const screen = await render(<MapScreen />);

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

    const resolveButton = await screen.findByText("Resolve");

    fireEvent.press(resolveButton);

    await waitFor(() => {
      expect(mockedConfirmReport).toHaveBeenCalledWith("r_9001", "resolved");
    });

    expect(screen.queryByTestId("login-required-modal")).toBeNull();
  });
});

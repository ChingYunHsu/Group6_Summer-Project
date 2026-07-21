import { Alert } from "react-native";
import { act, fireEvent, render } from "@testing-library/react-native";

import ReportModal from "../../components/ReportModal";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// This component has no t() defaultValue fallbacks anywhere (unlike most
// other files tonight), so without a real i18next instance configured,
// t(key) would just return the raw key string. Rather than guess at
// readable text that might not actually render, every query in this file
// goes through the testIDs added directly to ReportModal.tsx for exactly
// this reason.

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

/* -------------------------------------------------------------------------- */
/*                                  FIXTURES                                  */
/* -------------------------------------------------------------------------- */

import { Venue } from "../../types/venue";

// Type-asserted rather than fully populated — ReportModal.tsx only ever
// reads venue_id/name/venue_type/latitude/longitude from a Venue object
// (confirmed directly from its source), and Venue itself has 20+ other
// required fields (borough, phone, opening_hours, rating, etc.) that are
// completely irrelevant to what this component actually does with it.
const mockVenue = {
  venue_id: "v_1",
  name: "Test Clinic",
  venue_type: "clinic",
  latitude: 40.7527,
  longitude: -73.9772,
  address: "1 Test St",
  active_warning: 0,
  accessible_status: "unknown",
} as unknown as Venue;

const mockCurrentLocation = { latitude: 40.75, longitude: -73.98 };

const baseProps = {
  visible: true,
  isAuthenticated: true,
  locationEnabled: true,
  currentLocation: mockCurrentLocation,
  nearbyVenues: [mockVenue],
  onClose: jest.fn(),
  onRequireLogin: jest.fn(),
  onRequireLocation: jest.fn(),
  onSubmitVenue: jest.fn(),
  onSubmitIncident: jest.fn(),
};

/* -------------------------------------------------------------------------- */
/*                                   TESTS                                    */
/* -------------------------------------------------------------------------- */
//
// NOTE (RNTL v14): render, fireEvent, and act are all async now — they
// return Promises that must be awaited, or the state update they trigger
// won't have flushed before the next line runs. Every fireEvent call below
// is awaited for that reason. pressAlertButton() invokes an Alert button's
// onPress directly (bypassing fireEvent entirely, since Alert buttons
// aren't real rendered elements), so that call is wrapped in act() instead
// to flush the state updates it causes.

describe("ReportModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Alert, "alert");
  });

  // Alert.alert's buttons are passed as data, not rendered as real
  // tappable elements in the test renderer — "tapping" one means
  // capturing the mock call's arguments and invoking that button's
  // onPress directly.
  async function pressAlertButton(buttonIndex = 0) {
    const alertCall = (Alert.alert as jest.Mock).mock.calls[0];
    const buttons = alertCall[2];
    await act(async () => {
      buttons[buttonIndex].onPress();
    });
  }

  it("blocks a guest from submitting: shows a login alert instead of calling onSubmitVenue/onSubmitIncident", async () => {
    const screen = await render(
      <ReportModal {...baseProps} isAuthenticated={false} />,
    );

    await fireEvent.press(screen.getByTestId("report-mode-incident"));
    await fireEvent.press(screen.getByTestId("report-issue-large_crowd"));
    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(Alert.alert).toHaveBeenCalled();
    expect(baseProps.onSubmitVenue).not.toHaveBeenCalled();
    expect(baseProps.onSubmitIncident).not.toHaveBeenCalled();

    await pressAlertButton();

    expect(baseProps.onRequireLogin).toHaveBeenCalled();
  });

  // A real asymmetry confirmed directly in ReportModal.tsx's own
  // handleSubmit — the login-required path calls handleClose() AND
  // onRequireLogin(), but the location-required path only calls
  // onRequireLocation(), leaving the modal open. Testing the actual
  // written behaviour, not an assumption of what it "should" do.
  it("blocks submission without location enabled: shows a location alert and leaves the modal open", async () => {
    const screen = await render(
      <ReportModal {...baseProps} locationEnabled={false} />,
    );

    await fireEvent.press(screen.getByTestId("report-mode-incident"));
    await fireEvent.press(screen.getByTestId("report-issue-large_crowd"));
    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(Alert.alert).toHaveBeenCalled();
    expect(baseProps.onSubmitVenue).not.toHaveBeenCalled();
    expect(baseProps.onSubmitIncident).not.toHaveBeenCalled();

    await pressAlertButton();

    expect(baseProps.onRequireLocation).toHaveBeenCalled();
    expect(baseProps.onClose).not.toHaveBeenCalled();
  });

  it("submits a venue-bound report with the venue's own coordinates, not the user's current location", async () => {
    const screen = await render(<ReportModal {...baseProps} />);

    await fireEvent.press(screen.getByTestId("report-mode-venue"));
    await fireEvent.press(screen.getByTestId("report-venue-row-v_1"));
    await fireEvent.press(screen.getByTestId("report-issue-elevator_broken"));

    await fireEvent.changeText(
      screen.getByTestId("report-description-input"),
      "Elevator has been broken since this morning",
    );

    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(baseProps.onSubmitVenue).toHaveBeenCalledWith(
      expect.objectContaining({
        venueId: "v_1",
        issueType: "elevator_broken",
        description: "Elevator has been broken since this morning",
        latitude: mockVenue.latitude,
        longitude: mockVenue.longitude,
      }),
    );

    expect(baseProps.onSubmitIncident).not.toHaveBeenCalled();
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it("submits a standalone incident report with the user's current location, no venue required", async () => {
    const screen = await render(<ReportModal {...baseProps} />);

    await fireEvent.press(screen.getByTestId("report-mode-incident"));
    await fireEvent.press(
      screen.getByTestId("report-issue-protest_or_blockage"),
    );

    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(baseProps.onSubmitIncident).toHaveBeenCalledWith(
      expect.objectContaining({
        issueType: "protest_or_blockage",
        latitude: mockCurrentLocation.latitude,
        longitude: mockCurrentLocation.longitude,
      }),
    );

    expect(baseProps.onSubmitVenue).not.toHaveBeenCalled();
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it("keeps the submit button disabled until an issue type is selected", async () => {
    const screen = await render(<ReportModal {...baseProps} />);

    await fireEvent.press(screen.getByTestId("report-mode-incident"));

    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(baseProps.onSubmitIncident).not.toHaveBeenCalled();
  });

  it("keeps the submit button disabled for a venue report until a venue is actually selected", async () => {
    const screen = await render(<ReportModal {...baseProps} />);

    await fireEvent.press(screen.getByTestId("report-mode-venue"));

    // Confirmed in ReportModal.tsx: in venue mode, visibleIssues is derived
    // from the selected venue's venue_type, so the issue-type grid renders
    // nothing at all until a venue is picked — there is no issue button to
    // press yet. Deliberately not pressing report-venue-row-v_1.
    expect(screen.queryByTestId("report-issue-elevator_broken")).toBeNull();

    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(baseProps.onSubmitVenue).not.toHaveBeenCalled();
  });

  it("resets mode/venue/issueType/description after a successful submission", async () => {
    const screen = await render(<ReportModal {...baseProps} />);

    await fireEvent.press(screen.getByTestId("report-mode-venue"));
    await fireEvent.press(screen.getByTestId("report-venue-row-v_1"));
    await fireEvent.press(screen.getByTestId("report-issue-elevator_broken"));
    await fireEvent.press(screen.getByTestId("report-submit-button"));

    expect(baseProps.onClose).toHaveBeenCalled();

    // Mode is reset to null — Step 2/3 (venue list, issue grid) should no
    // longer be rendered, confirming resetState() actually ran rather
    // than just onClose() being called with stale internal state.
    expect(screen.queryByTestId("report-venue-row-v_1")).toBeNull();
    expect(screen.queryByTestId("report-issue-elevator_broken")).toBeNull();
  });
});

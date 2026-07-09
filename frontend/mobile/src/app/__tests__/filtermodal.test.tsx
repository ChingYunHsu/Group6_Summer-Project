import { fireEvent, render } from "@testing-library/react-native";

import FilterModal from "../../components/FilterModal";

describe("FilterModal", () => {
  const mockClose = jest.fn();
  const mockApply = jest.fn();

  const defaultProps = {
    visible: true,
    openNow: false,
    accessible: false,
    // A language *code*, matching FilterModal's real contract (it compares
    // against featuredLanguages[].code, e.g. "fr") — not a display name.
    language: "fr",
    autoCurrentTime: true,
    onClose: mockClose,
    onApply: mockApply,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders Live Status when Auto Current Time is enabled", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    expect(screen.getByText("Live Status")).toBeTruthy();

    expect(screen.getByText("Quiet")).toBeTruthy();

    expect(screen.queryByTestId("date-selector")).toBeNull();

    expect(screen.queryByTestId("time-selector")).toBeNull();
  });

  it("renders manual date and time controls when Auto Current Time is disabled", async () => {
    const screen = await render(
      <FilterModal {...defaultProps} autoCurrentTime={false} />,
    );

    expect(screen.queryByText("Live Status")).toBeNull();

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

  it("shows Live Status after enabling Auto Current Time", async () => {
    const screen = await render(
      <FilterModal {...defaultProps} autoCurrentTime={false} />,
    );

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", true);

    expect(screen.getByText("Live Status")).toBeTruthy();

    expect(screen.queryByTestId("date-selector")).toBeNull();

    expect(screen.queryByTestId("time-selector")).toBeNull();
  });

  // Reverse direction of the test above — the existing suite only covered
  // disabled→enabled via interaction; this covers enabled→disabled, so
  // both toggle states are verified via actual user interaction, not just
  // via initial props.
  it("shows manual date/time controls after disabling Auto Current Time", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", false);

    expect(screen.queryByText("Live Status")).toBeNull();

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

  // Toggling is staged local state, not a live-apply — this guards against
  // a regression where flipping the switch alone would fire onApply
  // before the user presses the Apply button.
  it("does not call onApply just from toggling the switch", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", false);

    expect(mockApply).not.toHaveBeenCalled();
  });

  it("calls onApply when Apply Filters is pressed", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    fireEvent.press(screen.getByTestId("apply-filters-button"));

    expect(mockApply).toHaveBeenCalled();
  });

  it("calls onClose after applying filters", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    fireEvent.press(screen.getByText("Apply Filters"));

    expect(mockClose).toHaveBeenCalled();
  });

  it("passes the Auto Current Time value to onApply from initial props", async () => {
    const screen = await render(
      <FilterModal {...defaultProps} autoCurrentTime={false} />,
    );

    fireEvent.press(screen.getByText("Apply Filters"));

    expect(mockApply).toHaveBeenCalledWith(
      expect.objectContaining({
        autoCurrentTime: false,
      }),
    );
  });

  // Same assertion as above, but exercised through the actual switch
  // interaction rather than only the initial prop — verifies the staged
  // local state that gets sent to onApply, not just the prop passthrough.
  it("passes the toggled Auto Current Time value to onApply after interaction", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", false);

    fireEvent.press(screen.getByTestId("apply-filters-button"));

    expect(mockApply).toHaveBeenCalledWith(
      expect.objectContaining({
        autoCurrentTime: false,
      }),
    );
  });
});

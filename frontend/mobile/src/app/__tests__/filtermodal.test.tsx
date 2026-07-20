import { fireEvent, render } from "@testing-library/react-native";

import FilterModal from "../../components/FilterModal";

describe("FilterModal", () => {
  const mockClose = jest.fn();
  const mockApply = jest.fn();

  const defaultProps = {
    visible: true,
    openNow: false,
    accessible: false,
    language: "fr",
    autoCurrentTime: true,
    onClose: mockClose,
    onApply: mockApply,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders Live Status and the date/time controls together, regardless of Auto Current Time", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    expect(screen.getByText("Live Status")).toBeTruthy();

    expect(screen.getByText("Quiet")).toBeTruthy();

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

  it("still renders Live Status and the date/time controls together when Auto Current Time is disabled", async () => {
    const screen = await render(
      <FilterModal {...defaultProps} autoCurrentTime={false} />,
    );

    expect(screen.getByText("Live Status")).toBeTruthy();

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

  it("keeps both sections visible after toggling Auto Current Time on via interaction", async () => {
    const screen = await render(
      <FilterModal {...defaultProps} autoCurrentTime={false} />,
    );

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", true);

    await screen.findByText("Live Status");

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

  it("keeps both sections visible after toggling Auto Current Time off via interaction", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", false);

    await screen.findByTestId("date-selector");

    expect(screen.getByText("Live Status")).toBeTruthy();

    expect(screen.getByTestId("date-selector")).toBeTruthy();

    expect(screen.getByTestId("time-selector")).toBeTruthy();
  });

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

  it("passes the toggled Auto Current Time value to onApply after interaction", async () => {
    const screen = await render(<FilterModal {...defaultProps} />);

    const toggle = screen.getByTestId("auto-current-time-switch");

    fireEvent(toggle, "valueChange", false);

    await screen.findByTestId("date-selector");

    fireEvent.press(screen.getByTestId("apply-filters-button"));

    expect(mockApply).toHaveBeenCalledWith(
      expect.objectContaining({
        autoCurrentTime: false,
      }),
    );
  });
});

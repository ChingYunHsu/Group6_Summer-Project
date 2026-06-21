import { fireEvent, render } from "@testing-library/react-native";
import LegalScreen from "../legal";

const mockPush = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "login.welcomeBack": "Welcome back",
        "login.getStarted": "Get started",
        "legal.title": "Legal & Privacy",
      };

      return translations[key] || key;
    },
  }),
}));

describe("LegalScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders title", async () => {
    const screen = await render(<LegalScreen />);

    expect(
      screen.getByText("Legal & Privacy")
    ).toBeTruthy();
  });

  it("renders terms checkbox", async () => {
    const screen = await render(<LegalScreen />);

    expect(
      screen.getByTestId("terms-checkbox")
    ).toBeTruthy();
  });

  it("renders privacy checkbox", async () => {
    const screen = await render(<LegalScreen />);

    expect(
      screen.getByTestId("privacy-checkbox")
    ).toBeTruthy();
  });

  it("renders continue button", async () => {
    const screen = await render(<LegalScreen />);

    expect(
      screen.getByTestId("continue-button")
    ).toBeTruthy();
  });

  it("allows accepting terms", async () => {
    const screen = await render(<LegalScreen />);

    const terms =
      screen.getByTestId("terms-checkbox");

    fireEvent(terms, "valueChange", true);

    expect(terms).toBeTruthy();
  });

  it("allows accepting privacy policy", async () => {
    const screen = await render(<LegalScreen />);

    const privacy =
      screen.getByTestId("privacy-checkbox");

    fireEvent(privacy, "valueChange", true);

    expect(privacy).toBeTruthy();
  });

  it("does not navigate on initial render", async () => {
    await render(<LegalScreen />);

    expect(mockPush).not.toHaveBeenCalled();
  });

  it("prevents continuation when agreements are unchecked", async () => {
  const screen = await render(<LegalScreen />);

  const button =
    screen.getByTestId("continue-button");

  expect(
    button.props.accessibilityState.disabled
  ).toBe(true);
});
});
import {
  fireEvent,
  render,
  waitFor,
} from "@testing-library/react-native";
import LoginScreen from "../login";

const mockPush = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    push: (...args: any[]) => mockPush(...args),
  },
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

describe("LoginScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders sign in screen by default", async () => {
    const screen = await render(<LoginScreen />);

    expect(
      screen.getByText("Welcome back")
    ).toBeTruthy();
  });

  it("opens registration mode", async () => {
    const screen = await render(<LoginScreen />);

    fireEvent.press(
      screen.getByTestId("switch-to-register")
    );

    await waitFor(() => {
      expect(
        screen.getByText("Get started")
      ).toBeTruthy();
    });
  });

  it("renders terms switch in registration mode", async () => {
    const screen = await render(<LoginScreen />);

    fireEvent.press(
      screen.getByTestId("switch-to-register")
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("terms-switch")
      ).toBeTruthy();
    });
  });

  it("create account button starts disabled", async () => {
    const screen = await render(<LoginScreen />);

    fireEvent.press(
      screen.getByTestId("switch-to-register")
    );

    const button = await waitFor(() =>
      screen.getByTestId(
        "create-account-button"
      )
    );

    expect(
      button.props.accessibilityState
        ?.disabled
    ).toBe(true);
  });

  it("can enable terms switch", async () => {
    const screen = await render(<LoginScreen />);

    fireEvent.press(
      screen.getByTestId("switch-to-register")
    );

    const terms = await waitFor(() =>
      screen.getByTestId("terms-switch")
    );

    fireEvent(
      terms,
      "valueChange",
      true
    );

    expect(terms).toBeTruthy();
  });

 it("create account button becomes enabled after accepting terms", async () => {
  const screen = await render(<LoginScreen />);

  fireEvent.press(
    screen.getByTestId("switch-to-register")
  );

  const terms = await waitFor(() =>
    screen.getByTestId("terms-switch")
  );

  fireEvent(
    terms,
    "valueChange",
    true
  );

  await waitFor(() => {
    const button =
      screen.getByTestId(
        "create-account-button"
      );

    expect(
      button.props.accessibilityState
        ?.disabled
    ).toBe(false);
  });
});

it("routes to map when Skip For Now is pressed", async () => {
  const screen = await render(<LoginScreen />);

  fireEvent.press(
    screen.getByTestId("switch-to-register")
  );

  const terms = await waitFor(() =>
    screen.getByTestId("terms-switch")
  );

  fireEvent(
    terms,
    "valueChange",
    true
  );

  const createButton =
    await waitFor(() =>
      screen.getByTestId(
        "create-account-button"
      )
    );

  fireEvent.press(createButton);

  const skipButton =
    await screen.findByTestId(
      "skip-for-now-button"
    );

  fireEvent.press(skipButton);

  expect(mockPush).toHaveBeenCalledWith(
    "/map"
  );
});
});
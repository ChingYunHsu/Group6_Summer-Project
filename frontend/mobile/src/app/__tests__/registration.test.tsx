import { Alert } from "react-native";
import { fireEvent, render, waitFor } from "@testing-library/react-native";

import LoginScreen from "../login";
import { login, register } from "../../services/authService";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    push: (...args: any[]) => mockPush(...args),
    replace: (...args: any[]) => mockReplace(...args),
    back: jest.fn(),
  },
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock("../../services/authService", () => ({
  login: jest.fn(),
  register: jest.fn(),
}));

const mockedLogin = login as jest.Mock;
const mockedRegister = register as jest.Mock;

describe("LoginScreen — Sign in", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Alert, "alert");
  });

  it("calls login() with the entered email and password, then routes to /map on success", async () => {
    mockedLogin.mockResolvedValue(undefined);

    const screen = await render(<LoginScreen />);

    await fireEvent.changeText(
      screen.getByTestId("login-email-input"),
      "david@example.com",
    );
    await fireEvent.changeText(
      screen.getByTestId("login-password-input"),
      "correct-password",
    );

    await fireEvent.press(screen.getByText("login.signIn"));

    await waitFor(() => {
      expect(mockedLogin).toHaveBeenCalledWith(
        "david@example.com",
        "correct-password",
      );
    });

    expect(mockReplace).toHaveBeenCalledWith("/map");
  });

  it("shows an error alert and does not navigate when login() fails", async () => {
    mockedLogin.mockRejectedValue(new Error("Invalid credentials"));

    const screen = await render(<LoginScreen />);

    await fireEvent.changeText(
      screen.getByTestId("login-email-input"),
      "david@example.com",
    );
    await fireEvent.changeText(
      screen.getByTestId("login-password-input"),
      "wrong-password",
    );

    await fireEvent.press(screen.getByText("login.signIn"));

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        "login.signInErrorTitle",
        "Invalid credentials",
      );
    });

    expect(mockReplace).not.toHaveBeenCalledWith("/map");
  });
});

describe("LoginScreen — Registration submission", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Alert, "alert");
  });

  async function fillRegistrationForm(screen: any) {
    await fireEvent.press(screen.getByTestId("switch-to-register"));

    await fireEvent.changeText(
      await screen.findByTestId("login-fullname-input"),
      "David Irving",
    );
    await fireEvent.changeText(
      screen.getByTestId("login-email-input"),
      "david@example.com",
    );
    await fireEvent.changeText(
      screen.getByTestId("login-password-input"),
      "a-real-password",
    );

    await fireEvent(screen.getByTestId("terms-switch"), "valueChange", true);
  }

  it("calls register() with the entered fullName, email, and password", async () => {
    mockedRegister.mockResolvedValue({ finish_profile_prompt: false });

    const screen = await render(<LoginScreen />);

    await fillRegistrationForm(screen);

    await fireEvent.press(screen.getByTestId("create-account-button"));

    await waitFor(() => {
      expect(mockedRegister).toHaveBeenCalledWith(
        "David Irving",
        "david@example.com",
        "a-real-password",
      );
    });
  });

  // The existing login.test.tsx only ever mocks finish_profile_prompt as
  // true — this covers the other real branch, where registration
  // succeeds but the modal is skipped entirely.
  it("routes straight to /map with no modal when finish_profile_prompt is false", async () => {
    mockedRegister.mockResolvedValue({ finish_profile_prompt: false });

    const screen = await render(<LoginScreen />);

    await fillRegistrationForm(screen);

    await fireEvent.press(screen.getByTestId("create-account-button"));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/map");
    });

    expect(screen.queryByTestId("finish-profile-button")).toBeNull();
    expect(screen.queryByTestId("skip-for-now-button")).toBeNull();
  });

  it("Finish Profile navigates to /map then pushes /medical-id, in that order", async () => {
    mockedRegister.mockResolvedValue({ finish_profile_prompt: true });

    const screen = await render(<LoginScreen />);

    await fillRegistrationForm(screen);

    await fireEvent.press(screen.getByTestId("create-account-button"));

    const finishButton = await screen.findByTestId("finish-profile-button");

    await fireEvent.press(finishButton);

    expect(mockReplace).toHaveBeenCalledWith("/map");
    expect(mockPush).toHaveBeenCalledWith("/medical-id");

    // Order matters here specifically — replace() has to happen before
    // push(), not just "both eventually called" — confirmed via each
    // mock's own invocation order.
    const replaceOrder = mockReplace.mock.invocationCallOrder[0];
    const pushOrder = mockPush.mock.invocationCallOrder[0];
    expect(replaceOrder).toBeLessThan(pushOrder);
  });

  it("shows the generic error message when register() fails without field-specific details", async () => {
    mockedRegister.mockRejectedValue(new Error("Something went wrong"));

    const screen = await render(<LoginScreen />);

    await fillRegistrationForm(screen);

    await fireEvent.press(screen.getByTestId("create-account-button"));

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        "login.registerErrorTitle",
        "Something went wrong",
      );
    });
  });

  it("appends missing/invalid field names to the error message when the backend provides them", async () => {
    const fieldError: any = new Error("Validation failed.");
    fieldError.body = {
      missing_fields: ["password"],
      invalid_fields: ["email"],
    };
    mockedRegister.mockRejectedValue(fieldError);

    const screen = await render(<LoginScreen />);

    await fillRegistrationForm(screen);

    await fireEvent.press(screen.getByTestId("create-account-button"));

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        "login.registerErrorTitle",
        "Validation failed. (password, email)",
      );
    });
  });
});

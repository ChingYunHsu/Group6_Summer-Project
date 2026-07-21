import { Alert } from "react-native";
import { fireEvent, render, waitFor } from "@testing-library/react-native";

import LoginScreen from "../login";
import { login, register } from "../../services/authService";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// Companion to the existing login.test.tsx, not a replacement — that file
// already covers mode-switching and the terms-switch/button-enabling UI
// well. This file specifically covers what it didn't: handleSignIn
// entirely, the "Finish Profile" modal button (only "Skip For Now" was
// previously tested), the no-modal-needed registration path, and
// registration's field-specific error handling.
//
// NOTE (RNTL v14): fireEvent is async now and must be awaited, or the
// state update it triggers (including async handlers like handleSignIn /
// handleCreateAccount, which await login()/register() before calling
// setLoading) won't be flushed before the next line runs. Every
// fireEvent call below is awaited for that reason.

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

  // The other real modal button, never previously tested — only "Skip
  // For Now" was. handleFinishProfile does replace() THEN push(), in
  // that specific order, for a real documented reason (avoiding a stale
  // login form sitting underneath in navigation history) — confirmed
  // directly against login.tsx's own comment on that function.
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

  // Real, non-trivial logic in login.tsx's own catch block — extracting
  // missing_fields/invalid_fields from the error body and appending them
  // to the message, so the user sees specifically which field failed
  // rather than just a generic failure. Confirmed directly against the
  // source; previously had zero coverage at all.
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

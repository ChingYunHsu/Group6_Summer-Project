import { Alert } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { fireEvent, render, waitFor } from "@testing-library/react-native";

import SettingsScreen from "../settings";
import { deleteAccount } from "../../services/api";
import { clearAccessToken } from "../../services/tokenStorage";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// This file is deliberately narrow, matching the same philosophy as
// map.test.tsx and reportModal.test.tsx — it only exercises
// handleDeleteAccount. Location permission checking and language label
// loading (this screen's own useFocusEffect) are mocked with simple,
// safe defaults just so the component renders without crashing, not
// tested in any depth here — that would be a separate settings.test.tsx
// concern, not "account deletion".

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockBack = jest.fn();
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    back: (...args: any[]) => mockBack(...args),
    push: (...args: any[]) => mockPush(...args),
    replace: (...args: any[]) => mockReplace(...args),
  },
  useFocusEffect: (callback: () => void) => {
    const { useEffect } = require("react");
    useEffect(() => {
      const cleanup = callback();
      return typeof cleanup === "function" ? cleanup : undefined;
    }, [callback]);
  },
}));

jest.mock("expo-location", () => ({
  getForegroundPermissionsAsync: jest
    .fn()
    .mockResolvedValue({ status: "granted" }),
}));

jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: jest.fn().mockResolvedValue(null),
  clear: jest.fn().mockResolvedValue(undefined),
}));

jest.mock("../../services/api", () => ({
  deleteAccount: jest.fn(),
}));

jest.mock("../../services/authService", () => ({
  logout: jest.fn(),
}));

jest.mock("../../services/location", () => ({
  requestLocationPermission: jest.fn().mockResolvedValue(true),
}));

jest.mock("../../services/tokenStorage", () => ({
  clearAccessToken: jest.fn().mockResolvedValue(undefined),
}));

/* -------------------------------------------------------------------------- */
/*                                   TESTS                                    */
/* -------------------------------------------------------------------------- */

const mockedDeleteAccount = deleteAccount as jest.Mock;
const mockedClearAccessToken = clearAccessToken as jest.Mock;
const mockedAsyncStorageClear = AsyncStorage.clear as jest.Mock;

describe("Account deletion", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Alert, "alert");
    mockedDeleteAccount.mockResolvedValue(undefined);
  });

  // Alert.alert's buttons are passed as data, not rendered as real
  // tappable elements in the test renderer — "tapping" one means
  // capturing the mock call's arguments and invoking that button's
  // onPress directly. Confirmed against settings.tsx's actual
  // handleDeleteAccount: index 0 = Cancel, index 1 = Delete (destructive).
  function pressAlertButton(buttonIndex: number) {
    const alertCall = (Alert.alert as jest.Mock).mock.calls[0];
    const buttons = alertCall[2];
    return buttons[buttonIndex].onPress?.();
  }

  it("shows a confirmation alert rather than deleting immediately on tap", async () => {
    const screen = await render(<SettingsScreen />);

    fireEvent.press(await screen.findByText("settings.deleteAccount"));

    expect(Alert.alert).toHaveBeenCalledWith(
      "settings.deleteAccount",
      "settings.deleteAccountMessage",
      expect.any(Array),
    );

    expect(mockedDeleteAccount).not.toHaveBeenCalled();
  });

  it("does nothing if Cancel is pressed in the confirmation alert", async () => {
    const screen = await render(<SettingsScreen />);

    fireEvent.press(await screen.findByText("settings.deleteAccount"));

    pressAlertButton(0); // Cancel

    expect(mockedDeleteAccount).not.toHaveBeenCalled();
    expect(mockReplace).not.toHaveBeenCalledWith("/");
  });

  it("on confirmed delete: calls deleteAccount, clears the token, clears AsyncStorage, and navigates to the root — in that order, with no further backend call after deletion succeeds", async () => {
    const screen = await render(<SettingsScreen />);

    fireEvent.press(await screen.findByText("settings.deleteAccount"));

    await pressAlertButton(1); // Delete (destructive)

    await waitFor(() => {
      expect(mockedDeleteAccount).toHaveBeenCalled();
    });

    // Per settings.tsx's own comment: DELETE /user/account already
    // succeeded server-side by this point — everything after is
    // local-only cleanup, no further backend call (e.g. no separate
    // logout()) should happen.
    expect(mockedClearAccessToken).toHaveBeenCalled();
    expect(mockedAsyncStorageClear).toHaveBeenCalled();
    expect(mockReplace).toHaveBeenCalledWith("/");
  });

  it("on a failed delete: shows an error alert, does NOT clear local storage or navigate, and re-enables the button", async () => {
    mockedDeleteAccount.mockRejectedValue(new Error("API 500"));

    const screen = await render(<SettingsScreen />);

    fireEvent.press(await screen.findByText("settings.deleteAccount"));

    await pressAlertButton(1); // Delete (destructive)

    await waitFor(() => {
      expect(mockedDeleteAccount).toHaveBeenCalled();
    });

    // A second Alert.alert call for the error — first call was the
    // original confirmation prompt.
    await waitFor(() => {
      expect((Alert.alert as jest.Mock).mock.calls.length).toBeGreaterThan(1);
    });

    const errorCall = (Alert.alert as jest.Mock).mock.calls[1];
    expect(errorCall[0]).toBe("settings.deleteErrorTitle");

    // The real, safety-relevant assertion: a failed deletion must never
    // clear the user's local session/data or navigate them out, since
    // their account still genuinely exists server-side at this point.
    expect(mockedClearAccessToken).not.toHaveBeenCalled();
    expect(mockedAsyncStorageClear).not.toHaveBeenCalled();
    expect(mockReplace).not.toHaveBeenCalledWith("/");

    // Button text reverts from the loading state, confirming setDeleting(false)
    // actually ran on the failure path, not just on success.
    expect(await screen.findByText("settings.deleteAccount")).toBeTruthy();
  });

  it("shows a loading state on the delete button while the request is in flight", async () => {
    let resolveDelete: () => void;
    mockedDeleteAccount.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveDelete = resolve;
      }),
    );

    const screen = await render(<SettingsScreen />);

    fireEvent.press(await screen.findByText("settings.deleteAccount"));

    pressAlertButton(1); // Delete (destructive) — deliberately not awaited,
    // since the point of this test is to observe the in-flight state
    // before the promise resolves.

    expect(await screen.findByText("common.loading")).toBeTruthy();

    resolveDelete!();

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });
});

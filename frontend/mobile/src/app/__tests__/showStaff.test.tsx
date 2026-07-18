import React from "react";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import { AppState } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

import ShowStaffScreen from "../(tabs)/show-staff";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockBack = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    push: (...args: any[]) => mockPush(...args),
    replace: (...args: any[]) => mockReplace(...args),
    back: (...args: any[]) => mockBack(...args),
  },
  useFocusEffect: (callback: () => void | (() => void)) => {
    const { useEffect } = require("react");
    useEffect(() => {
      const cleanup = callback();
      return typeof cleanup === "function" ? cleanup : undefined;
    }, [callback]);
    // [callback] as the dependency, not [] and not no-array. The real
    // callback is wrapped in useCallback(fn, [someRealDep]) by the
    // component itself, so React's own reference-equality check on
    // [callback] here naturally mirrors that: it only re-fires when the
    // component's OWN dependency actually changed (e.g. authStatus
    // transitioning), never on every unrelated re-render. A no-array
    // version re-fired on every single render regardless of cause,
    // which caused a genuine infinite loop in any screen whose state
    // update produces a new object reference each time (e.g. storing a
    // freshly-looked-up language object) — confirmed via a runaway,
    // unpasteable screen.debug() dump and repeated overlapping act()
    // warnings once evidence was actually gathered.
  },
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const knownTranslations: Record<string, string> = {
        "showStaff.title": "Show Staff",
        "showStaff.visitorSpeaks": "This visitor speaks",
        "showStaff.commonPhrases": "Common Phrases",
        "showStaff.liveTranslate": "Live Translate",
        "showStaff.translationPlaceholder": "Type in the visitor's language...",
        "showStaff.translationResult":
          "Translation will appear here after backend integration.",
        "showStaff.medicalSummary": "Medical ID Summary",
        "profile.fullName": "Full Name",
        "profile.bloodType": "Blood Type",
        "profile.conditions": "Conditions",
        "profile.allergies": "Allergies",
        "profile.phone": "Phone",
      };

      if (key.startsWith("showStaff.categories.")) {
        return key.replace("showStaff.categories.", "");
      }

      if (key in knownTranslations) return knownTranslations[key];

      if (options && typeof options === "object" && "defaultValue" in options) {
        return options.defaultValue as string;
      }

      return key;
    },
  }),
}));

jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

jest.mock("../../services/api", () => ({
  translateText: jest.fn(),
}));

jest.mock("../../services/authService", () => ({
  getAccessToken: jest.fn(),
}));

jest.mock("../../services/medicalIdService", () => ({
  loadMedicalId: jest.fn(),
}));

jest.mock("../../services/profileService", () => ({
  loadProfile: jest.fn(),
}));

jest.mock("expo-speech", () => ({
  speak: jest.fn(),
  stop: jest.fn(),
}));

jest.mock("expo-clipboard", () => ({
  setStringAsync: jest.fn(() => Promise.resolve()),
}));

jest.mock("expo-brightness", () => ({
  getBrightnessAsync: jest.fn(() => Promise.resolve(0.5)),
  setBrightnessAsync: jest.fn(() => Promise.resolve()),
}));

const { translateText } = require("../../services/api");
const { getAccessToken } = require("../../services/authService");
const { loadMedicalId } = require("../../services/medicalIdService");
const { loadProfile } = require("../../services/profileService");

beforeEach(() => {
  jest.clearAllMocks();
  getAccessToken.mockResolvedValue(null);
  jest
    .spyOn(AppState, "addEventListener")
    .mockReturnValue({ remove: jest.fn() } as any);
});

// Defensive, regardless of exactly why a given test might not reach its
// own jest.useRealTimers() call (a failed assertion partway through, an
// unexpected error, etc.) — without this, fake timers from one test can
// leak into the next and break its findBy*/waitFor calls in exactly the
// way already diagnosed once in this file (fake timers active before a
// findBy* call means it can never resolve, since that polling relies on
// real timers internally).
afterEach(() => {
  jest.useRealTimers();
});

describe("ShowStaffScreen — language switching", () => {
  it("shows the visitor's language badge matching whatever is currently stored", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("fr");

    const screen = await render(<ShowStaffScreen />);

    expect(await screen.findByText(/Français/)).toBeTruthy();
  });

  it("shows German when that's what's currently stored", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("de");
    const screen = await render(<ShowStaffScreen />);

    expect(await screen.findByText(/Deutsch/)).toBeTruthy();
  });

  // Same underlying concern as the test above — does the language effect
  // genuinely re-read AsyncStorage on each fresh invocation, rather than
  // reading it once and caching that value forever — demonstrated via
  // two independent tests with different stored values, rather than one
  // test manually unmounting and remounting mid-test. The manual
  // unmount+remount pattern was tried and confirmed (via three separate
  // fix attempts, all unsuccessful) to leak something into whichever
  // test ran immediately afterward, even in isolation from the
  // useFocusEffect mock itself. Letting @testing-library/react-native's
  // own between-test cleanup do this instead sidesteps that entirely —
  // each test gets a genuinely fresh instance the normal way.
  it("shows Spanish when that's what's currently stored — confirming a fresh mount isn't reading a cached value from elsewhere", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("es");
    const screen = await render(<ShowStaffScreen />);

    expect(await screen.findByText(/Español/)).toBeTruthy();
  });
});

describe("ShowStaffScreen — graceful handling of network failures and incomplete backend responses", () => {
  it("shows a real translation on success", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("es");
    translateText.mockResolvedValue({
      translatedText: "My chest hurts",
      sourceLanguage: "es",
      targetLanguage: "en",
    });

    const screen = await render(<ShowStaffScreen />);
    const input = await screen.findByPlaceholderText(/visitor's language/i);

    fireEvent.changeText(input, "Me duele el pecho");

    // No fake timers here at all, deliberately — after four separate
    // attempts to make jest.useFakeTimers()/advanceTimersByTimeAsync/
    // runAllTimersAsync play nicely with RNTL's own polling (each
    // confirmed, via direct isolated-vs-full-suite testing, to leak
    // something into whichever test ran next despite passing on its own
    // merits), the simplest fix turned out to be avoiding the
    // interaction entirely. Real 1200ms debounce, real wall-clock wait —
    // findByText's default 1000ms window is shorter than that on its
    // own, so it's extended explicitly rather than relying on the
    // default.
    expect(
      await screen.findByText("My chest hurts", {}, { timeout: 3000 }),
    ).toBeTruthy();
  }, 10000);

  it("shows a distinct, tappable login-required message for a 401 — not a generic failure", async () => {
    const authError: any = new Error("Unauthorized");
    authError.status = 401;
    translateText.mockRejectedValue(authError);

    const screen = await render(<ShowStaffScreen />);
    const input = await screen.findByPlaceholderText(/visitor's language/i);

    fireEvent.changeText(input, "Hola");

    const loginPrompt = await screen.findByText(
      /Log in to use Live Translate/i,
      {},
      { timeout: 3000 },
    );
    expect(loginPrompt).toBeTruthy();

    fireEvent.press(loginPrompt);
    expect(mockPush).toHaveBeenCalledWith("/login");
  }, 10000);

  it("shows a distinct rate-limited message for a 429 — confirmed live against the real backend, not hypothetical", async () => {
    const rateLimitError: any = new Error("Too Many Requests");
    rateLimitError.status = 429;
    translateText.mockRejectedValue(rateLimitError);

    const screen = await render(<ShowStaffScreen />);
    const input = await screen.findByPlaceholderText(/visitor's language/i);

    fireEvent.changeText(input, "Hola");

    expect(
      await screen.findByText(
        /Too many translations at once/i,
        {},
        { timeout: 3000 },
      ),
    ).toBeTruthy();
  }, 10000);

  it("shows the generic failure message for anything else (e.g. a 503 from Gemini being down)", async () => {
    const serverError: any = new Error("Service Unavailable");
    serverError.status = 503;
    translateText.mockRejectedValue(serverError);

    const screen = await render(<ShowStaffScreen />);
    const input = await screen.findByPlaceholderText(/visitor's language/i);

    fireEvent.changeText(input, "Hola");

    expect(
      await screen.findByText(
        /Translation failed. Please try again/i,
        {},
        { timeout: 3000 },
      ),
    ).toBeTruthy();
  }, 10000);

  it("does not attempt the medical summary fetch at all for a guest", async () => {
    getAccessToken.mockResolvedValue(null);

    await render(<ShowStaffScreen />);

    await waitFor(() => {
      expect(loadProfile).not.toHaveBeenCalled();
      expect(loadMedicalId).not.toHaveBeenCalled();
    });
  });
});

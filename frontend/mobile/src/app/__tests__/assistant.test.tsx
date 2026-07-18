import React from "react";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

import AssistantScreen from "../(tabs)/assistant";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockBack = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    push: (...args: any[]) => mockPush(...args),
    replace: (...args: any[]) => mockReplace(...args),
    back: (...args: any[]) => mockBack(...args),
  },
  // assistant.tsx reloads the stored language via useFocusEffect (fixed
  // from a mount-only useEffect — the original bug was that a language
  // change made elsewhere never got picked up on returning to this tab).
  // Running the callback once on render is the closest honest
  // approximation of "this screen just gained focus" available in a
  // unit test without pulling in expo-router/testing-library's full
  // renderRouter machinery.
  useFocusEffect: (callback: () => void | (() => void)) => {
    const { useEffect } = require("react");
    useEffect(() => {
      const cleanup = callback();
      return typeof cleanup === "function" ? cleanup : undefined;
    });
    // No dependency array, deliberately — the real callback passed in is
    // wrapped in useCallback(fn, [someState]) by the component itself,
    // so it becomes a genuinely new function reference whenever that
    // state changes. An empty array here meant this only ever ran once
    // on mount and never noticed those later changes (e.g. authStatus
    // going from checking to authenticated), which was silently causing
    // loadProfile/loadMedicalId/etc. to never be called at all.
  },
}));

// Superset of login.test.tsx's i18next mock: same per-file
// known-translations dictionary pattern, plus a defaultValue fallback
// for the many newer t(key, {defaultValue}) calls added throughout this
// project that a key-only dictionary can't resolve. Falls back to
// returning the raw key only if a call matches neither.
jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const knownTranslations: Record<string, string> = {
        "tabs.assistant": "Assistant",
      };

      if (key in knownTranslations) return knownTranslations[key];

      if (options && typeof options === "object" && "defaultValue" in options) {
        let value = options.defaultValue as string;
        Object.keys(options).forEach((optionKey) => {
          if (optionKey !== "defaultValue") {
            value = value.replace(`{{${optionKey}}}`, options[optionKey]);
          }
        });
        return value;
      }

      return key;
    },
  }),
}));

jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

jest.mock("../../services/api", () => ({
  sendChatbotMessage: jest.fn(),
  getVenue: jest.fn(),
}));

const { sendChatbotMessage, getVenue } = require("../../services/api");

const REAL_CHATBOT_RESPONSE = {
  message: "The nearest pharmacy is CVS Pharmacy Midtown.",
  language: "en",
  detected_language: "en",
  citations: ["venue:seed-pharmacy-cvs-midtown-001"],
  suggested_prompts: ["Find an urgent care near me"],
  fallback_used: false,
  response_time_ms: 1200,
};

const REAL_VENUE = {
  venue_id: "seed-pharmacy-cvs-midtown-001",
  name: "CVS Pharmacy Midtown",
  venue_type: "pharmacy",
  open_now: true,
  latitude: "40.7564090",
  longitude: "-73.9855880",
};

beforeEach(() => {
  jest.clearAllMocks();
  (AsyncStorage.getItem as jest.Mock).mockResolvedValue("en");
});

// fireEvent.changeText followed immediately by fireEvent.press, with
// nothing in between, was letting the button fire before the TextInput's
// controlled value/state update had actually flushed through a
// re-render — confirmed directly via screen.debug(), which showed
// value="" still sitting on the input at the moment of the press. This
// waits for the value to genuinely reflect what was typed before
// anything else touches the input, rather than assuming the two events
// land in the right order.
async function typeMessage(
  screen: Awaited<ReturnType<typeof render>>,
  text: string,
) {
  const input = screen.getByPlaceholderText("Ask a question...");
  fireEvent.changeText(input, text);

  await waitFor(() => {
    expect(input.props.value).toBe(text);
  });

  return input;
}

describe("AssistantScreen — chatbot rendering", () => {
  it("renders the two initial greeting messages on mount", async () => {
    const screen = await render(<AssistantScreen />);

    expect(
      await screen.findByText(/Hello! I'm your ClearPath Assistant/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/I can help find clinics, explain services/i),
    ).toBeTruthy();

    await act(async () => {});
  });

  it("sends a message and renders the real response, including a resolved venue citation card", async () => {
    sendChatbotMessage.mockResolvedValue(REAL_CHATBOT_RESPONSE);
    getVenue.mockResolvedValue(REAL_VENUE);

    const screen = await render(<AssistantScreen />);

    await typeMessage(screen, "Where is my nearest pharmacy?");
    fireEvent.press(screen.getByTestId("send-button"));

    await waitFor(() => {
      expect(sendChatbotMessage).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Where is my nearest pharmacy?" }),
      );
    });

    expect(
      await screen.findByText(/The nearest pharmacy is CVS Pharmacy Midtown/i),
    ).toBeTruthy();

    await waitFor(() => {
      expect(getVenue).toHaveBeenCalledWith("seed-pharmacy-cvs-midtown-001");
    });
    expect(await screen.findByText("CVS Pharmacy Midtown")).toBeTruthy();

    // The message list is a FlatList/VirtualizedList, which schedules its
    // own internal setTimeout to defer cell-rendering calculations —
    // completely separate from anything mocked above. If that timer is
    // still pending when this test ends, it fires during the NEXT test's
    // act() scope instead, producing "overlapping act() calls" and
    // cascading failures in unrelated tests later in the file. This
    // final empty act() flush lets any such pending work settle here,
    // before RNTL's automatic cleanup runs.
    await act(async () => {});
  });

  it("shows suggested prompts as tappable chips, and tapping one sends it as a new message", async () => {
    sendChatbotMessage.mockResolvedValue(REAL_CHATBOT_RESPONSE);
    getVenue.mockResolvedValue(REAL_VENUE);

    const screen = await render(<AssistantScreen />);

    await typeMessage(screen, "Hello");
    fireEvent.press(screen.getByTestId("send-button"));

    const promptChip = await screen.findByText("Find an urgent care near me");
    sendChatbotMessage.mockClear();

    fireEvent.press(promptChip);

    await waitFor(() => {
      expect(sendChatbotMessage).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Find an urgent care near me" }),
      );
    });

    await act(async () => {});
  });
});

describe("AssistantScreen — graceful handling of network failures", () => {
  it("shows the error message and does not crash when sendChatbotMessage rejects", async () => {
    sendChatbotMessage.mockRejectedValue(new Error("Network request failed"));

    const screen = await render(<AssistantScreen />);

    await typeMessage(screen, "Is anyone there?");
    fireEvent.press(screen.getByTestId("send-button"));

    expect(
      await screen.findByText(/Sorry, I couldn't get a response/i),
    ).toBeTruthy();

    await act(async () => {});
  });

  it("does not crash if a citation's venue fails to resolve", async () => {
    sendChatbotMessage.mockResolvedValue(REAL_CHATBOT_RESPONSE);
    getVenue.mockRejectedValue(new Error("404"));

    const screen = await render(<AssistantScreen />);

    await typeMessage(screen, "Where's the pharmacy?");
    fireEvent.press(screen.getByTestId("send-button"));

    expect(
      await screen.findByText(/The nearest pharmacy is CVS Pharmacy Midtown/i),
    ).toBeTruthy();

    await act(async () => {});
  });
});

describe("AssistantScreen — language switching", () => {
  it("shows the stored language's native name in the header before any message is sent", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("es");

    const screen = await render(<AssistantScreen />);

    // The exact bug found and fixed live: respondingLanguageLabel was
    // pulling .english ("Spanish") instead of .native ("Español") in
    // both of its branches.
    expect(await screen.findByText(/Español/)).toBeTruthy();

    await act(async () => {});
  });

  it("re-reads the stored language on focus, not just on first mount", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce("en");
    const screen = await render(<AssistantScreen />);
    await screen.findByText(/Responding in English/);

    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("fr");
    await screen.rerender(<AssistantScreen />);

    expect(await screen.findByText(/Français/)).toBeTruthy();

    await act(async () => {});
  });

  it("switches to the response's own detected_language once a real reply comes back, overriding the stored preference", async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue("en");
    sendChatbotMessage.mockResolvedValue({
      ...REAL_CHATBOT_RESPONSE,
      detected_language: "es",
      message: "La farmacia más cercana es CVS Pharmacy Midtown.",
    });
    getVenue.mockResolvedValue(REAL_VENUE);

    const screen = await render(<AssistantScreen />);

    await typeMessage(screen, "¿Dónde está la farmacia?");
    fireEvent.press(screen.getByTestId("send-button"));

    expect(await screen.findByText(/Español/)).toBeTruthy();

    await act(async () => {});
  });
});

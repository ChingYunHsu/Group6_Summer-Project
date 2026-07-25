import React from "react";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";

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
  useFocusEffect: (callback: () => void | (() => void)) => {
    const { useEffect } = require("react");
    useEffect(() => {
      const cleanup = callback();
      return typeof cleanup === "function" ? cleanup : undefined;
    });
  },
}));

// Superset of login.test.tsx's i18next mock: same per-file
// known-translations dictionary pattern, plus a defaultValue fallback
// for the many newer t(key, {defaultValue}) calls added throughout this
// project that a key-only dictionary can't resolve. Falls back to
// returning the raw key only if a call matches neither.
jest.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty", init: jest.fn() },
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

// assistant.tsx reads the current language directly off i18n.language
// (synchronous, in-memory) rather than AsyncStorage. Mocking i18n itself, with a
// plain mutable `language` property, lets tests drive that the same way
// production code changes it (i18n.changeLanguage() updates this
// synchronously with no disk round-trip). `t` here only needs to cover
// the two greeting keys assistant.tsx re-translates on a language
// change; it returns each call's defaultValue, same fallback behaviour
// as the react-i18next mock above.
jest.mock("../../i18n", () => ({
  __esModule: true,
  default: {
    language: "en",
    t: (key: string, options?: any) =>
      options && typeof options === "object" && "defaultValue" in options
        ? (options.defaultValue as string)
        : key,
  },
}));

const mockI18n = require("../../i18n").default;

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
  mockI18n.language = "en";
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
    mockI18n.language = "es";

    const screen = await render(<AssistantScreen />);

    expect(await screen.findByText(/Español/)).toBeTruthy();

    await act(async () => {});
  });

  it("re-reads the stored language on focus, not just on first mount", async () => {
    mockI18n.language = "en";
    const screen = await render(<AssistantScreen />);
    await screen.findByText(/Responding in English/);

    mockI18n.language = "fr";
    await screen.rerender(<AssistantScreen />);

    expect(await screen.findByText(/Français/)).toBeTruthy();

    await act(async () => {});
  });

  it("switches to the response's own detected_language once a real reply comes back, overriding the stored preference", async () => {
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

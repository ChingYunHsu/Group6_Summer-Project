import React from "react";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import { Linking } from "react-native";

import SOSScreen from "../sos";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockBack = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    push: (...args: any[]) => mockPush(...args),
    replace: (...args: any[]) => mockReplace(...args),
    back: (...args: any[]) => mockBack(...args),
  },
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const knownTranslations: Record<string, string> = {
        "sos.title": "Preparing Emergency Call",
        "sos.subtitle": "Your emergency call will begin unless cancelled.",
        "sos.cancel": "Cancel Emergency Call",
        "sos.locationTitle": "Current Location",
        "sos.locationDescription":
          "Your location is available to share during the emergency call.",
        "sos.medicalIdTitle": "Medical ID Summary",
        "sos.bloodType": "Blood Type",
        "sos.conditions": "Conditions",
        "sos.allergies": "Allergies",
        "sos.none": "None",
        "sos.notProvided": "Not provided",
        "sos.notice":
          "Keep this screen available while speaking with the emergency operator.",
        "sos.callErrorTitle": "Unable to place call",
        "sos.callErrorMessage": "This device cannot make phone calls.",
      };

      if (key === "sos.countdown") {
        return `Calling in ${options?.seconds}s`;
      }

      if (key in knownTranslations) return knownTranslations[key];

      if (options && typeof options === "object" && "defaultValue" in options) {
        return options.defaultValue as string;
      }

      return key;
    },
  }),
}));

jest.mock("../../services/authService", () => ({
  getAccessToken: jest.fn(),
}));

jest.mock("../../services/api", () => ({
  getEmergencyContacts: jest.fn(),
}));

jest.mock("../../services/location", () => ({
  getCurrentLocation: jest.fn(),
  requestLocationPermission: jest.fn(() => Promise.resolve(true)),
}));

jest.mock("../../services/medicalIdService", () => ({
  loadMedicalId: jest.fn(),
}));

jest.mock("expo-location", () => ({
  hasServicesEnabledAsync: jest.fn(() => Promise.resolve(true)),
  reverseGeocodeAsync: jest.fn(() =>
    Promise.resolve([
      {
        streetNumber: "150",
        street: "E 42nd St",
        city: "New York",
        region: "NY",
        postalCode: "10017",
      },
    ]),
  ),
}));

const { getAccessToken } = require("../../services/authService");
const { getEmergencyContacts } = require("../../services/api");
const { getCurrentLocation } = require("../../services/location");
const { loadMedicalId } = require("../../services/medicalIdService");

const REAL_MEDICAL_ID = {
  blood_type: "O+",
  conditions: ["Asthma", "Hypertension"],
  allergies: ["Penicillin", "Latex"],
};

const REAL_EMERGENCY_CONTACT = {
  contact_id: "ec_001",
  name: "Sarah Miller",
  relationship: "Sister",
  phone: "+15550123456",
};

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(Linking, "canOpenURL").mockResolvedValue(true);
  jest.spyOn(Linking, "openURL").mockResolvedValue(undefined as any);
  getCurrentLocation.mockResolvedValue({
    latitude: 40.758,
    longitude: -73.9855,
  });
});

describe("SOSScreen — countdown and auto-dial", () => {
  it("cancel navigates back and does not place a call", async () => {
    getAccessToken.mockResolvedValue(null);

    const screen = await render(<SOSScreen />);

    fireEvent.press(screen.getByText(/Cancel Emergency Call/i));

    expect(mockBack).toHaveBeenCalled();
    expect(Linking.openURL).not.toHaveBeenCalledWith("tel:911");
  });
});

describe("SOSScreen — medical profile rendering (summary card)", () => {
  it("renders real blood type, conditions, and allergies for a logged-in user", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadMedicalId.mockResolvedValue(REAL_MEDICAL_ID);
    getEmergencyContacts.mockResolvedValue({
      count: 1,
      items: [REAL_EMERGENCY_CONTACT],
    });

    const screen = await render(<SOSScreen />);

    expect(await screen.findByText("O+")).toBeTruthy();
    expect(await screen.findByText(/Asthma, Hypertension/)).toBeTruthy();
    expect(await screen.findByText(/Penicillin, Latex/)).toBeTruthy();
  });

  it("shows 'None' for a confirmed-empty conditions/allergies list, not the same as unknown", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadMedicalId.mockResolvedValue({
      blood_type: "AB-",
      conditions: [],
      allergies: [],
    });
    getEmergencyContacts.mockResolvedValue({ count: 0, items: [] });

    const screen = await render(<SOSScreen />);

    await screen.findByText("AB-");
    expect(screen.getAllByText("None").length).toBeGreaterThanOrEqual(1);
  });

  it("skips the medical fetch entirely for a guest, rather than firing a call that will just 401", async () => {
    getAccessToken.mockResolvedValue(null);

    await render(<SOSScreen />);

    await waitFor(() => {
      expect(loadMedicalId).not.toHaveBeenCalled();
      expect(getEmergencyContacts).not.toHaveBeenCalled();
    });
  });
});

describe("SOSScreen — graceful handling of network failures", () => {
  it("does not crash if loadMedicalId rejects, and shows 'Not provided' rather than empty/broken UI", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadMedicalId.mockRejectedValue(new Error("API 500"));
    getEmergencyContacts.mockResolvedValue({ count: 0, items: [] });

    const screen = await render(<SOSScreen />);

    // "Not provided" legitimately appears multiple times when the
    // medical fetch fails (every field falls back to it) — findByText
    // throws on multiple matches by design, so findAllByText is the
    // right tool here: the actual thing being tested is "at least one
    // graceful fallback rendered," not "exactly one field shows it."
    const fallbacks = await screen.findAllByText("Not provided");
    expect(fallbacks.length).toBeGreaterThan(0);
  });

  it("does not crash and shows the unavailable message if location can't be resolved", async () => {
    getAccessToken.mockResolvedValue(null);
    getCurrentLocation.mockResolvedValue(null);

    const screen = await render(<SOSScreen />);

    expect(
      await screen.findByText(/Unable to determine your current location/i),
    ).toBeTruthy();
  });
});

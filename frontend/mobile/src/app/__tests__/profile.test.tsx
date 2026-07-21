import React from "react";
import { render, waitFor } from "@testing-library/react-native";

import ProfileScreen from "../(tabs)/profile";

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
        "profile.title": "Profile & Medical ID",
        "profile.userId": "User ID",
        "profile.fullName": "Full Name",
        "profile.email": "Email",
        "profile.phone": "Phone",
        "profile.dateOfBirth": "Date of Birth",
        "profile.gender": "Gender",
        "profile.nationality": "Nationality",
        "profile.languages": "Languages",
        "profile.address": "Address",
        "profile.medicalId": "Medical ID",
        "profile.bloodType": "Blood Type",
        "profile.conditions": "Conditions",
        "profile.allergies": "Allergies",
        "profile.savedClinics": "Saved Clinics",
        "profile.synced": "Medical information synced",
        "profile.lastUpdated": "Last updated 5 minutes ago",
        "editProfile.personalInformation": "Personal Information",
        "common.edit": "Edit",
      };

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

jest.mock("../../services/profileService", () => ({
  loadProfile: jest.fn(),
}));

jest.mock("../../services/medicalIdService", () => {
  const actual = jest.requireActual("../../services/medicalIdService");
  return {
    ...actual,
    loadMedicalId: jest.fn(),
  };
});

jest.mock("../../services/api", () => ({
  getFavourites: jest.fn(),
  getVenue: jest.fn(),
  removeFavourite: jest.fn(),
}));

const { getAccessToken } = require("../../services/authService");
const { loadProfile } = require("../../services/profileService");
const { loadMedicalId } = require("../../services/medicalIdService");
const { getFavourites } = require("../../services/api");

const REAL_PROFILE = {
  user_id: "22a244cc-0713-459b-97a9-3570afeaa5fe",
  email: "david.irving1@ucdconnect.ie",
  full_name: "David Irving",
  phone: "083 123 1234",
  nationality: "Irish",
  spoken_languages: ["French", "Spanish"],
};

const REAL_MEDICAL_ID = {
  date_of_birth: "1998-10-01",
  gender: "Male",
  address: "11 Hurricane Highway",
  blood_type: "O+",
  conditions: ["Asthma"],
  allergies: [],
};

beforeEach(() => {
  jest.clearAllMocks();
  getFavourites.mockResolvedValue({ count: 0, items: [] });
});

describe("ProfileScreen — protected page routing", () => {
  it("redirects a guest to profile-guest, and never renders mock or real profile content", async () => {
    getAccessToken.mockResolvedValue(null);

    const screen = await render(<ProfileScreen />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/profile-guest");
    });

    // The actual bug this guards against: mockProfile's static
    // placeholder ("Amelia Rivera") and real fetches that would just
    // 401 previously rendered/fired briefly before the redirect
    // completed, since the redirect was a separate, uncoordinated effect
    // that didn't block anything else.
    expect(screen.queryByText("David Irving")).toBeNull();
    expect(loadProfile).not.toHaveBeenCalled();
    expect(loadMedicalId).not.toHaveBeenCalled();
  });

  it("does not redirect an authenticated user, and loads real content instead", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadProfile.mockResolvedValue(REAL_PROFILE);
    loadMedicalId.mockResolvedValue(REAL_MEDICAL_ID);

    const screen = await render(<ProfileScreen />);

    // "David Irving" genuinely appears twice in a correct render — once
    // in the header/avatar card, once again in the Full Name row — so
    // findByText throws on it by design (multiple matches). Confirmed
    // via a real rendered-tree dump: "22a244cc…" (the truncated User ID)
    // appears exactly once, making it a more reliable check here.
    expect(await screen.findByText("22a244cc…")).toBeTruthy();
    expect(mockReplace).not.toHaveBeenCalledWith("/profile-guest");
  });
});

describe("ProfileScreen — authentication state transitions", () => {
  it("shows no mock or real data while the auth check is still in flight", async () => {
    getAccessToken.mockReturnValue(new Promise(() => {}));

    const screen = await render(<ProfileScreen />);

    // mockProfile.full_name is "Amelia Rivera" — the specific static
    // placeholder this whole authStatus gate exists to keep off-screen
    // until auth is genuinely confirmed either way.
    expect(screen.queryByText(/Amelia Rivera/)).toBeNull();
    expect(screen.queryByText("David Irving")).toBeNull();
  });

  it("transitions from checking to authenticated and only then fetches profile/medical/favourites", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadProfile.mockResolvedValue(REAL_PROFILE);
    loadMedicalId.mockResolvedValue(REAL_MEDICAL_ID);

    await render(<ProfileScreen />);

    await waitFor(() => {
      expect(loadProfile).toHaveBeenCalled();
      expect(loadMedicalId).toHaveBeenCalled();
      expect(getFavourites).toHaveBeenCalled();
    });
  });
});

describe("ProfileScreen — medical profile rendering", () => {
  it("renders real blood type and conditions once authenticated", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadProfile.mockResolvedValue(REAL_PROFILE);
    loadMedicalId.mockResolvedValue(REAL_MEDICAL_ID);

    const screen = await render(<ProfileScreen />);

    expect(await screen.findByText("O+")).toBeTruthy();
    expect(await screen.findByText("Asthma")).toBeTruthy();
  });
});

describe("ProfileScreen — graceful handling of network failures", () => {
  it("shows an offline sync state, not a crash, when profile/medical fetches fail", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadProfile.mockRejectedValue(new Error("API 500"));
    loadMedicalId.mockRejectedValue(new Error("API 500"));

    const screen = await render(<ProfileScreen />);

    expect(await screen.findByText(/Offline/i)).toBeTruthy();
  });

  it("does not crash if favourites fails to load", async () => {
    getAccessToken.mockResolvedValue("real-token");
    loadProfile.mockResolvedValue(REAL_PROFILE);
    loadMedicalId.mockResolvedValue(REAL_MEDICAL_ID);
    getFavourites.mockRejectedValue(new Error("API 500"));

    const screen = await render(<ProfileScreen />);

    expect(await screen.findByText("22a244cc…")).toBeTruthy();
  });
});

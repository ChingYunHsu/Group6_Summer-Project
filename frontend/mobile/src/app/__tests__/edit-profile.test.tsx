import { Alert } from "react-native";
import { fireEvent, render, waitFor } from "@testing-library/react-native";

import EditProfileScreen from "../edit-profile";
import { loadProfile, saveProfile } from "../../services/profileService";
import { loadMedicalId, saveMedicalId } from "../../services/medicalIdService";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// edit-profile.tsx had zero testIDs before tonight — every selector below
// depends on the minimal set just added to the source file (Save button,
// dob/nationality/phone/address inputs, gender trigger + modal options,
// language add/search/option/remove controls). No behavioural changes.
//
// t() is mocked to honour defaultValue like real i18next does, unlike
// some other test files in this suite — editProfile.tsx leans heavily on
// defaultValue fallbacks and there's no reason to throw that away here.

const mockBack = jest.fn();

jest.mock("expo-router", () => ({
  router: {
    back: (...args: any[]) => mockBack(...args),
    push: jest.fn(),
    replace: jest.fn(),
  },
}));

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) =>
      options?.defaultValue ?? key,
  }),
}));

jest.mock("../../services/profileService", () => ({
  loadProfile: jest.fn(),
  saveProfile: jest.fn(),
}));

jest.mock("../../services/medicalIdService", () => ({
  loadMedicalId: jest.fn(),
  saveMedicalId: jest.fn(),
}));

const mockedLoadProfile = loadProfile as jest.Mock;
const mockedSaveProfile = saveProfile as jest.Mock;
const mockedLoadMedicalId = loadMedicalId as jest.Mock;
const mockedSaveMedicalId = saveMedicalId as jest.Mock;

/* -------------------------------------------------------------------------- */
/*                                  FIXTURES                                  */
/* -------------------------------------------------------------------------- */
//
// Values deliberately distinct from data/mockProfile.ts's own defaults, so
// a test only passes if the backend-loaded value actually overwrote the
// component's initial placeholder state — not because they happened to
// already match.

const loadedProfile = {
  full_name: "Jane Testerson",
  email: "jane.testerson@example.com",
  phone: "0851112222",
  nationality: "Norwegian",
  spoken_languages: ["English"],
};

const loadedMedical = {
  gender: "Female",
  address: "12 Grafton Street",
  date_of_birth: "1990-06-15",
};

describe("EditProfileScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Alert, "alert");
    mockedLoadProfile.mockResolvedValue(loadedProfile);
    mockedLoadMedicalId.mockResolvedValue(loadedMedical);
    mockedSaveProfile.mockResolvedValue(undefined);
    mockedSaveMedicalId.mockResolvedValue(undefined);
  });

  it("loads profile and medical data from the backend and populates the editable fields", async () => {
    const screen = await render(<EditProfileScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("edit-profile-nationality-input").props.value,
      ).toBe("Norwegian");
    });

    expect(screen.getByTestId("edit-profile-dob-input").props.value).toBe(
      "1990-06-15",
    );
    expect(screen.getByTestId("edit-profile-phone-input").props.value).toBe(
      "0851112222",
    );
    expect(screen.getByTestId("edit-profile-address-input").props.value).toBe(
      "12 Grafton Street",
    );
  });

  it("saves edited profile and medical fields together via saveProfile and saveMedicalId, then navigates back", async () => {
    const screen = await render(<EditProfileScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("edit-profile-nationality-input").props.value,
      ).toBe("Norwegian");
    });

    await fireEvent.changeText(
      screen.getByTestId("edit-profile-dob-input"),
      "1990-07-20",
    );
    await fireEvent.changeText(
      screen.getByTestId("edit-profile-nationality-input"),
      "Irish",
    );
    await fireEvent.changeText(
      screen.getByTestId("edit-profile-phone-input"),
      "0879998877",
    );
    await fireEvent.changeText(
      screen.getByTestId("edit-profile-address-input"),
      "48 Merrion Square",
    );

    await fireEvent.press(screen.getByTestId("edit-profile-save-button"));

    await waitFor(() => {
      expect(mockedSaveProfile).toHaveBeenCalledWith({
        phone: "0879998877",
        nationality: "Irish",
        spoken_languages: ["English"],
      });
    });

    expect(mockedSaveMedicalId).toHaveBeenCalledWith({
      date_of_birth: "1990-07-20",
      gender: "Female",
      address: "48 Merrion Square",
    });

    expect(mockBack).toHaveBeenCalled();
  });

  // Confirmed directly in edit-profile.tsx's handleSave — it uses
  // Promise.allSettled, not Promise.all, specifically so that one field
  // failing to save doesn't silently discard the other that succeeded.
  // The user still needs to be told something went wrong either way.
  it("shows an error alert and does not navigate back if either save call fails", async () => {
    mockedSaveProfile.mockResolvedValue(undefined);
    mockedSaveMedicalId.mockRejectedValue(new Error("network error"));

    const screen = await render(<EditProfileScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("edit-profile-nationality-input").props.value,
      ).toBe("Norwegian");
    });

    await fireEvent.press(screen.getByTestId("edit-profile-save-button"));

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        "Couldn't save everything",
        "Some of your changes didn't save. Please try again.",
      );
    });

    expect(mockBack).not.toHaveBeenCalled();
  });

  it("removes a spoken language, and the removal is reflected in the saved payload", async () => {
    mockedLoadProfile.mockResolvedValue({
      ...loadedProfile,
      spoken_languages: ["English", "Irish"],
    });

    const screen = await render(<EditProfileScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("edit-profile-remove-language-Irish"),
      ).toBeTruthy();
    });

    await fireEvent.press(
      screen.getByTestId("edit-profile-remove-language-Irish"),
    );

    await fireEvent.press(screen.getByTestId("edit-profile-save-button"));

    await waitFor(() => {
      expect(mockedSaveProfile).toHaveBeenCalledWith(
        expect.objectContaining({ spoken_languages: ["English"] }),
      );
    });
  });

  it("selects a new gender from the gender modal and includes it in the saved payload", async () => {
    const screen = await render(<EditProfileScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("edit-profile-nationality-input").props.value,
      ).toBe("Norwegian");
    });

    await fireEvent.press(screen.getByTestId("edit-profile-gender-trigger"));
    await fireEvent.press(
      screen.getByTestId("edit-profile-gender-option-Non-binary"),
    );

    await fireEvent.press(screen.getByTestId("edit-profile-save-button"));

    await waitFor(() => {
      expect(mockedSaveMedicalId).toHaveBeenCalledWith(
        expect.objectContaining({ gender: "Non-binary" }),
      );
    });
  });
});

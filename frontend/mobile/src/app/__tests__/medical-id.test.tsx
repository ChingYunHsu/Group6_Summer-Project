import {
  fireEvent,
  render,
  waitFor,
  within,
} from "@testing-library/react-native";

import MedicalIdScreen from "../medical-id";
import { loadProfile } from "../../services/profileService";
import { loadMedicalId, saveMedicalId } from "../../services/medicalIdService";
import type { MedicalProfile } from "../../services/medicalIdService";

/* -------------------------------------------------------------------------- */
/*                                   MOCKS                                    */
/* -------------------------------------------------------------------------- */
//
// medical-id.tsx had zero testIDs before tonight — every selector below
// depends on the minimal set just added to the source file (Save button,
// blood type trigger + options, condition/allergy add/input/add-button/
// remove-tag controls, name text). No behavioural changes.
//
// DEFAULT_MEDICAL_PROFILE is imported for real (requireActual) since
// medical-id.tsx uses it directly as initial state, not through a mocked
// function — only loadMedicalId/saveMedicalId need to be jest.fn()s.

jest.mock("../../services/medicalIdService", () => {
  const actual = jest.requireActual("../../services/medicalIdService");
  return {
    ...actual,
    loadMedicalId: jest.fn(),
    saveMedicalId: jest.fn(),
  };
});

jest.mock("../../services/profileService", () => ({
  loadProfile: jest.fn(),
}));

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
  initReactI18next: {
    type: "3rdParty",
    init: () => {},
  },
}));

const mockedLoadMedicalId = loadMedicalId as jest.Mock;
const mockedSaveMedicalId = saveMedicalId as jest.Mock;
const mockedLoadProfile = loadProfile as jest.Mock;

/* -------------------------------------------------------------------------- */
/*                                  FIXTURES                                  */
/* -------------------------------------------------------------------------- */

// Type-asserted rather than fully populated, matching the same rationale
// used for the Venue fixture in reportmodal.test.tsx — medical-id.tsx
// only ever reads the fields listed here from a MedicalProfile.
const loadedMedical = {
  blood_type: "O+",
  allergies: ["Penicillin"],
  conditions: ["Asthma"],
  medications: [],
  emergency_contacts: [],
  gender: "Female",
  address: "12 Grafton Street",
  date_of_birth: "1990-06-15",
} as unknown as MedicalProfile;

describe("MedicalIdScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedLoadMedicalId.mockResolvedValue(loadedMedical);
    mockedLoadProfile.mockResolvedValue({ full_name: "Jane Testerson" });
    mockedSaveMedicalId.mockResolvedValue(loadedMedical);
  });

  it("loads the medical profile and full name from the backend, populating blood type, conditions, and allergies", async () => {
    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("medical-id-name-text").props.children).toBe(
        "Jane Testerson",
      );
    });

    expect(
      within(screen.getByTestId("medical-id-blood-type-trigger")).getByText(
        "O+",
      ),
    ).toBeTruthy();
    expect(
      screen.getByTestId("medical-id-remove-condition-Asthma"),
    ).toBeTruthy();
    expect(
      screen.getByTestId("medical-id-remove-allergy-Penicillin"),
    ).toBeTruthy();
  });

  it("saves the selected blood type together with existing conditions/allergies via saveMedicalId, then navigates back", async () => {
    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Asthma"),
      ).toBeTruthy();
    });

    await fireEvent.press(screen.getByTestId("medical-id-blood-type-trigger"));
    await fireEvent.press(
      screen.getByTestId("medical-id-blood-type-option-A-"),
    );

    await fireEvent.press(screen.getByTestId("medical-id-save-button"));

    await waitFor(() => {
      expect(mockedSaveMedicalId).toHaveBeenCalledWith(
        expect.objectContaining({
          blood_type: "A-",
          conditions: ["Asthma"],
          allergies: ["Penicillin"],
          date_of_birth: "1990-06-15",
          gender: "Female",
          address: "12 Grafton Street",
        }),
      );
    });

    expect(mockBack).toHaveBeenCalled();
  });

  // Real, non-trivial logic in medical-id.tsx's own addCondition — a
  // case-insensitive duplicate check, confirmed directly against the
  // source. Verifying the invariant it protects (no duplicate tag ever
  // renders) rather than the modal's own open/closed state, since that
  // isn't what the guard clause is actually for.
  it("does not add a duplicate condition when it only differs by case", async () => {
    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Asthma"),
      ).toBeTruthy();
    });

    await fireEvent.press(
      screen.getByTestId("medical-id-add-condition-button"),
    );
    await fireEvent.changeText(
      screen.getByTestId("medical-id-condition-input"),
      "asthma",
    );
    await fireEvent.press(
      screen.getByTestId("medical-id-condition-add-button"),
    );

    expect(screen.queryAllByText("Asthma")).toHaveLength(1);
  });

  it("adds a genuinely new condition and reflects it in the save payload", async () => {
    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Asthma"),
      ).toBeTruthy();
    });

    await fireEvent.press(
      screen.getByTestId("medical-id-add-condition-button"),
    );
    await fireEvent.changeText(
      screen.getByTestId("medical-id-condition-input"),
      "Diabetes",
    );
    await fireEvent.press(
      screen.getByTestId("medical-id-condition-add-button"),
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Diabetes"),
      ).toBeTruthy();
    });

    await fireEvent.press(screen.getByTestId("medical-id-save-button"));

    await waitFor(() => {
      expect(mockedSaveMedicalId).toHaveBeenCalledWith(
        expect.objectContaining({ conditions: ["Asthma", "Diabetes"] }),
      );
    });
  });

  it("removes a condition via its tag, and the removal is reflected in the saved payload", async () => {
    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Asthma"),
      ).toBeTruthy();
    });

    await fireEvent.press(
      screen.getByTestId("medical-id-remove-condition-Asthma"),
    );

    await fireEvent.press(screen.getByTestId("medical-id-save-button"));

    await waitFor(() => {
      expect(mockedSaveMedicalId).toHaveBeenCalledWith(
        expect.objectContaining({ conditions: [] }),
      );
    });
  });

  // Confirmed directly in medical-id.tsx's handleSave — unlike
  // edit-profile.tsx, a failed save here shows no Alert at all, only
  // console.error, and the finally block still resets saving to false.
  // Testing the actual written behaviour rather than assuming an alert
  // exists.
  it("does not navigate back on a failed save, and resets the Save button out of its loading state", async () => {
    mockedSaveMedicalId.mockRejectedValue(new Error("network error"));

    const screen = await render(<MedicalIdScreen />);

    await waitFor(() => {
      expect(
        screen.getByTestId("medical-id-remove-condition-Asthma"),
      ).toBeTruthy();
    });

    await fireEvent.press(screen.getByTestId("medical-id-save-button"));

    await waitFor(() => {
      expect(mockedSaveMedicalId).toHaveBeenCalled();
    });

    expect(mockBack).not.toHaveBeenCalled();

    await waitFor(() => {
      expect(
        within(screen.getByTestId("medical-id-save-button")).getByText(
          "common.save",
        ),
      ).toBeTruthy();
    });
  });
});

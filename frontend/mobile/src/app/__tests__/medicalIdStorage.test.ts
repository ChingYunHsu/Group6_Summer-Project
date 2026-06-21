import * as SecureStore from "expo-secure-store";

import {
    loadMedicalId,
    saveMedicalId,
} from "../../services/medicalIdService";

jest.mock("expo-secure-store", () => ({
  setItemAsync: jest.fn(),
  getItemAsync: jest.fn(),
}));

describe("medicalIdStorage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("saves medical id data", async () => {
    const medicalId = {
      blood_type: "O+",
      conditions: ["Asthma"],
      allergies: ["Peanuts"],
    };

    await saveMedicalId(medicalId);

    expect(
      SecureStore.setItemAsync
    ).toHaveBeenCalledWith(
      "medical_id",
      JSON.stringify(medicalId)
    );
  });

  it("loads medical id data", async () => {
    const medicalId = {
      blood_type: "O+",
      allergies: ["Peanuts"],
      conditions: ["Asthma"],
    };

    (
      SecureStore.getItemAsync as jest.Mock
    ).mockResolvedValue(
      JSON.stringify(medicalId)
    );

    const result =
      await loadMedicalId();

    expect(result).toEqual(
      medicalId
    );
  });

  it("returns null when no medical id exists", async () => {
    (
      SecureStore.getItemAsync as jest.Mock
    ).mockResolvedValue(null);

    const result =
      await loadMedicalId();

    expect(result).toBeNull();
  });
});
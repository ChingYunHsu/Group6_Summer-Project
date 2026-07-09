import { request } from "../../services/api";
import {
  DEFAULT_MEDICAL_PROFILE,
  loadMedicalId,
  saveMedicalId,
} from "../../services/medicalIdService";

jest.mock("../../services/api", () => ({
  request: jest.fn(),
}));

const mockedRequest = request as jest.Mock;

describe("medicalIdService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("saves medical id data via the API", async () => {
    const medicalId = {
      blood_type: "O+",
      conditions: ["Asthma"],
      allergies: ["Peanuts"],
    };

    mockedRequest.mockResolvedValue({
      ...DEFAULT_MEDICAL_PROFILE,
      ...medicalId,
    });

    const result = await saveMedicalId(medicalId);

    expect(mockedRequest).toHaveBeenCalledWith("/user/medical-profile", {
      method: "PUT",
      body: JSON.stringify(medicalId),
    });

    expect(result.blood_type).toBe("O+");
    expect(result.conditions).toEqual(["Asthma"]);
    expect(result.allergies).toEqual(["Peanuts"]);
  });

  it("loads medical id data via the API", async () => {
    const medicalId = {
      ...DEFAULT_MEDICAL_PROFILE,
      blood_type: "O+",
      allergies: ["Peanuts"],
      conditions: ["Asthma"],
    };

    mockedRequest.mockResolvedValue(medicalId);

    const result = await loadMedicalId();

    expect(mockedRequest).toHaveBeenCalledWith("/user/medical-profile");
    expect(result).toEqual(medicalId);
  });

  // No medical profile set yet — api/medical.py's own
  // MEDICAL_PROFILE_DEFAULTS returns this same all-null/empty shape,
  // never null itself, so loadMedicalId should reflect that.
  it("returns the default empty profile shape when nothing has been set", async () => {
    mockedRequest.mockResolvedValue(DEFAULT_MEDICAL_PROFILE);

    const result = await loadMedicalId();

    expect(result).toEqual(DEFAULT_MEDICAL_PROFILE);
  });
});

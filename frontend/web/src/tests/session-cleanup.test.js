import { clearClinicalSessionData } from "../utils/sessionCleanup";

describe("Clinical session cleanup", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  test("wipes all clinical data from session memory", () => {
    sessionStorage.setItem(
      "clearPathClinicalPayload",
      JSON.stringify({ allergy: "Latex" })
    );
    sessionStorage.setItem("clearPathQrSyncToken", "mock-token-123");
    sessionStorage.setItem(
      "clearPathMedicalCardDraft",
      JSON.stringify({ blood_type: "O+" })
    );

    clearClinicalSessionData();

    expect(sessionStorage.getItem("clearPathClinicalPayload")).toBeNull();
    expect(sessionStorage.getItem("clearPathQrSyncToken")).toBeNull();
    expect(sessionStorage.getItem("clearPathMedicalCardDraft")).toBeNull();
  });
});
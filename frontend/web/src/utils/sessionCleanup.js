export function clearClinicalSessionData() {
  sessionStorage.removeItem("clearPathClinicalPayload");
  sessionStorage.removeItem("clearPathQrSyncToken");
  sessionStorage.removeItem("clearPathMedicalCardDraft");
}
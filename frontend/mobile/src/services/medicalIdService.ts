import { request } from "./api";

export type MedicalProfile = {
  date_of_birth: string | null;
  gender: string | null;
  address: string | null;
  blood_type: string | null;
  allergies: string[];
  conditions: string[];
  medications: string[];
  emergency_contacts: string[];
};

// Safe default/empty state — used as initial state before the real
// fetch resolves, and as a fallback shape for screens that need
// something non-null to render against.
export const DEFAULT_MEDICAL_PROFILE: MedicalProfile = {
  date_of_birth: null,
  gender: null,
  address: null,
  blood_type: null,
  allergies: [],
  conditions: [],
  medications: [],
  emergency_contacts: [],
};

// Fetches the current user's medical profile.
export async function loadMedicalId(): Promise<MedicalProfile> {
  return request<MedicalProfile>("/user/medical-profile");
}

// Saves (partial) changes to the medical profile.
export async function saveMedicalId(
  medicalId: Partial<MedicalProfile>,
): Promise<MedicalProfile> {
  return request<MedicalProfile>("/user/medical-profile", {
    method: "PUT",
    body: JSON.stringify(medicalId),
  });
}

// Deletes the medical profile entirely.
export async function deleteMedicalId() {
  return request<void>("/user/medical-profile", {
    method: "DELETE",
  });
}

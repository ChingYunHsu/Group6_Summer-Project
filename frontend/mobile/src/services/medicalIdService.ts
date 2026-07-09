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

// mockMedicalId (data/mockMedicalId.ts) is shaped like the old MedicalId
// interface — blood_type/allergies/conditions/medications/emergency_notes/
// medical_pass_title — which no longer matches MedicalProfile at all
// (missing date_of_birth/gender/address/emergency_contacts). Using it to
// seed state that later receives a real MedicalProfile causes a type
// error. This is the correctly-shaped alternative, matching api/medical.py's
// own MEDICAL_PROFILE_DEFAULTS/DEFAULT_PROFILE — everything null/empty
// until a real fetch resolves.
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

export async function loadMedicalId(): Promise<MedicalProfile> {
  return request<MedicalProfile>("/user/medical-profile");
}

export async function saveMedicalId(
  medicalId: Partial<MedicalProfile>,
): Promise<MedicalProfile> {
  return request<MedicalProfile>("/user/medical-profile", {
    method: "PUT",
    body: JSON.stringify(medicalId),
  });
}

export async function deleteMedicalId() {
  return request<void>("/user/medical-profile", {
    method: "DELETE",
  });
}

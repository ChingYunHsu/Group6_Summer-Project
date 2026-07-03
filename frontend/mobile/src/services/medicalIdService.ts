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

export async function loadMedicalId(): Promise<MedicalProfile> {
  return request<MedicalProfile>(
    "/user/medical-profile"
  );
}

export async function saveMedicalId(
  medicalId: Partial<MedicalProfile>
): Promise<MedicalProfile> {
  return request<MedicalProfile>(
    "/user/medical-profile",
    {
      method: "PUT",
      body: JSON.stringify(medicalId),
    }
  );
}

export async function deleteMedicalId() {
  return request<void>(
    "/user/medical-profile",
    {
      method: "DELETE",
    }
  );
}
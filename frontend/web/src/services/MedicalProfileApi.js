import { apiRequest } from "./apiClient";

export async function getMedicalProfile() {
  const data = await apiRequest("/user/medical-profile");

  return {
    ...data,
    allergies: data.allergies || [],
    medical_conditions: data.medical_conditions || data.conditions || [],
    conditions: data.conditions || data.medical_conditions || [],
    medications: data.medications || [],
    emergency_contacts: data.emergency_contacts || [],
  };
}

export function updateMedicalProfile(profileData) {
  return apiRequest("/user/medical-profile", {
    method: "PUT",
    body: JSON.stringify(profileData),
  });
}
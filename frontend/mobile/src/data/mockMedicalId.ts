import type { MedicalProfile } from "../services/medicalIdService";

export const mockMedicalId: MedicalProfile = {
  date_of_birth: null,
  gender: null,
  address: null,
  blood_type: "O+",
  allergies: ["Peanuts, Penicillin"],
  conditions: ["Asthma, Diabetes"],
  medications: ["Salbutamol Inhaler"],
  emergency_contacts: [],
};
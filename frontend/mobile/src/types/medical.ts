export interface MedicalId {
  date_of_birth: string;
  gender: string;
  address: string;
  blood_type: string;
  allergies: string[];
  medical_conditions: string[];
  emergency_contacts: { name: string; phone: string; relationship: string }[];
}
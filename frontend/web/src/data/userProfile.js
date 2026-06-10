export const USER_PROFILE = {
  full_name: "Amelia Rivera",
  email: "amelia.rivera@example.com",
  phone: "+1 (917) 555-0118",
  date_of_birth: "1998-04-12",
  gender: "Female",
  nationality: "Spanish",
  address: "245 W 46th St, New York, NY 10036",
  blood_type: "O+",
  donor_status: "Universal Donor",
  spoken_languages: [
    "Spanish (Native)",
    "English (Fluent)",
    "French (Intermediate)",
  ],
  allergies: [
    { name: "Penicillin", detail: "Severe reaction (Anaphylaxis)" },
    { name: "Latex", detail: "Mild skin irritation" },
  ],
  conditions: [
    { name: "Asthma", detail: "Diagnosed 2005. Managed with Albuterol PRN." },
    { name: "Hypothyroidism", detail: "Daily Levothyroxine 50mcg." },
  ],
  emergency_contacts: [
    {
      name: "Marcus Rostova",
      relationship: "Spouse",
      phone: "+41 79 987 65 43",
      primary: true,
    },
    {
      name: "Dr. Sarah Mueller",
      relationship: "Primary Care Physician",
      phone: "+41 44 111 22 33",
      primary: false,
    },
  ],
};

export const LANGUAGE_OPTIONS = [
  { code: "en", native_name: "English", english_name: "English" },
  { code: "fr", native_name: "Français", english_name: "French" },
  { code: "es", native_name: "Español", english_name: "Spanish" },
  { code: "zh", native_name: "中文", english_name: "Chinese" },
  { code: "ar", native_name: "العربية", english_name: "Arabic" },
];

export const EMERGENCY_CONTACTS = [
  {
    name: "Marcus Rivera",
    relationship: "Spouse",
    phone: "+1 (917) 555-0199",
  },
];
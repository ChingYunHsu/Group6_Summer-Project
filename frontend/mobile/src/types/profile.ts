export interface UserProfile {
  user_id: string;
  account_state: string;
  full_name: string;
  email: string;
  phone: string;
  date_of_birth: string;
  gender: string;
  nationality: string;
  address: string;
  spoken_languages: string[];
  guest_prompt_title: string;
  avatar_initials: string;
}

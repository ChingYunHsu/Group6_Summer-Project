import { mockProfile } from "../data/mockProfile";
import { request } from "./api";

export type UserProfile = typeof mockProfile;

// Matches get_user_profile()'s actual SELECT in backend/src/api/user.py:
//   SELECT display_name, phone, nationality, spoken_languages FROM users
// The column is `display_name`, not `full_name` — the previous version of
// this type claimed `full_name`, `user_id`, and `email` were all present,
// none of which the backend actually returns. Reading .full_name off the
// raw response was silently always undefined; mapped explicitly below so
// the rest of the app can keep using UserProfile.full_name as before.
type ProfileResponse = {
  display_name: string;
  phone: string;
  nationality: string;
  spoken_languages: string[];
};

function mergeProfileResponse(profile: ProfileResponse): UserProfile {
  // A freshly registered account has never had phone/nationality/
  // spoken_languages set — register_user() only inserts user_id, email,
  // password_hash, display_name — so these legitimately come back null
  // from the backend, not just as a hypothetical edge case. Falling back
  // to mockProfile's stale placeholder text would be worse than an empty
  // value, so these fall back to genuinely empty values instead, and
  // spoken_languages specifically falls back to [] since callers (e.g.
  // edit-profile.tsx) call .join() on it directly.
  return {
    ...mockProfile,
    full_name: profile.display_name ?? mockProfile.full_name,
    phone: profile.phone ?? "",
    nationality: profile.nationality ?? "",
    spoken_languages: profile.spoken_languages ?? [],
  };
}

export async function loadProfile(): Promise<UserProfile> {
  const profile = await request<ProfileResponse>("/user/profile");

  return mergeProfileResponse(profile);
}

export async function saveProfile(profile: {
  phone?: string;
  nationality?: string;
  spoken_languages?: string[];
}): Promise<UserProfile> {
  const updatedProfile = await request<ProfileResponse>("/user/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });

  return mergeProfileResponse(updatedProfile);
}

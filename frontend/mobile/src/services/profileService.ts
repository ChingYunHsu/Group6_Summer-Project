import { mockProfile } from "../data/mockProfile";
import { request } from "./api";

export type UserProfile = typeof mockProfile;

type ProfileResponse = {
  user_id: string;
  email: string;
  full_name: string;
  phone: string;
  nationality: string;
  spoken_languages: string[];
};

// Merges a real API response into the full UserProfile shape, falling
// back to mockProfile's fields for anything the response leaves out —
// keeps every screen able to rely on the full shape existing, rather
// than having to optional-chain every field individually.
function mergeProfileResponse(profile: ProfileResponse): UserProfile {
  return {
    ...mockProfile,
    user_id: profile.user_id ?? mockProfile.user_id,
    email: profile.email ?? mockProfile.email,
    full_name: profile.full_name ?? mockProfile.full_name,
    phone: profile.phone ?? "",
    nationality: profile.nationality ?? "",
    spoken_languages: profile.spoken_languages ?? [],
  };
}

// Fetches the current user's profile.
export async function loadProfile(): Promise<UserProfile> {
  const profile = await request<ProfileResponse>("/user/profile");

  return mergeProfileResponse(profile);
}

// Saves (partial) changes to the profile — only phone/nationality/
// spoken_languages are actually editable server-side.
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

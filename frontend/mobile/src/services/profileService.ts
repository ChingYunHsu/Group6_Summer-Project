import { mockProfile } from "../data/mockProfile";
import { request } from "./api";

export type UserProfile = typeof mockProfile;

type ProfileResponse = {
  user_id: string;
  full_name: string;
  email: string;
  phone: string;
  nationality: string;
  spoken_languages: string[];
};

export async function loadProfile(): Promise<UserProfile> {
  const profile =
    await request<ProfileResponse>(
      "/user/profile"
    );

  return {
    ...mockProfile,
    ...profile,
  };
}

export async function saveProfile(
  profile: {
    phone?: string;
    nationality?: string;
    spoken_languages?: string[];
  }
): Promise<UserProfile> {
  const updatedProfile =
    await request<ProfileResponse>(
      "/user/profile",
      {
        method: "PUT",
        body: JSON.stringify(profile),
      }
    );

  return {
    ...mockProfile,
    ...updatedProfile,
  };
}
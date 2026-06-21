import * as SecureStore from "expo-secure-store";

const PROFILE_KEY = "medical_profile";

export async function saveProfile(
  profile: unknown
) {
  await SecureStore.setItemAsync(
    PROFILE_KEY,
    JSON.stringify(profile)
  );
}

export async function loadProfile() {
  const data =
    await SecureStore.getItemAsync(
      PROFILE_KEY
    );

  return data ? JSON.parse(data) : null;
}
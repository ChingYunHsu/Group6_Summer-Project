import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "access_token";

// Reads the stored auth token, or null if none is saved.
export async function getAccessToken() {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

// Saves the auth token after a successful login/registration.
export async function saveAccessToken(token: string) {
  return SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

// Clears the stored token — used on logout, account deletion, and
// session-expiry handling in api.ts.
export async function clearAccessToken() {
  return SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
}

import { apiRequest } from "./apiClient";

export function getUserProfile() {
  return apiRequest("/user/profile");
}

export function updateUserProfile(profileData) {
  return apiRequest("/user/profile", {
    method: "PUT",
    body: JSON.stringify(profileData),
  });
}
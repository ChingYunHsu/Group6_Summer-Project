import { apiRequest } from "./apiClient";

export function getUserProfile() {
  return apiRequest("/user/profile");
}

export function updateUserProfile(updates) {
  return apiRequest("/user/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });
}

export function deleteAccount() {
  return apiRequest("/user/account", {
    method: "DELETE",
  });
}
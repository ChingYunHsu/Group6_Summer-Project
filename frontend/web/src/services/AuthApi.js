import { apiRequest } from "./apiClient";

export function resetPassword(email) {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });
}
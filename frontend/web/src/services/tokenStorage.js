export function saveAuthData(data) {
  localStorage.setItem("access_token", data.access_token || "");
  localStorage.setItem("refresh_token", data.refresh_token || "");
  localStorage.setItem("user_id", data.user_id || "");
  localStorage.setItem("token_type", data.token_type || "bearer");
}

export function getAccessToken() {
  return localStorage.getItem("access_token");
}

export function clearAuthData() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user_id");
  localStorage.removeItem("token_type");
}
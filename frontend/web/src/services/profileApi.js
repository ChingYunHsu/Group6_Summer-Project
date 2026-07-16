const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function getAccessToken() {
  return localStorage.getItem("access_token");
}

export async function getMedicalProfile() {
  const accessToken = getAccessToken();

  if (!accessToken) {
    throw new Error("Missing access token");
  }

  const authHeader = accessToken.startsWith("Bearer ")
    ? accessToken
    : `Bearer ${accessToken}`;

  const response = await fetch(`${API_BASE_URL}/api/v1/user/medical-profile`, {
    method: "GET",
    headers: {
      Authorization: authHeader,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      `Medical profile request failed: ${response.status} ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}
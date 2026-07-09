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

  const response = await fetch("/api/v1/user/medical-profile", {
    method: "GET",
    headers: {
      Authorization: authHeader,
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
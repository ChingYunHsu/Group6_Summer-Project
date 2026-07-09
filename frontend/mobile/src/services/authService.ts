import { request } from "./api";
import {
  clearAccessToken,
  getAccessToken,
  saveAccessToken,
} from "./tokenStorage";

// Re-exported so every existing `import { getAccessToken } from "./authService"`
// elsewhere in the app (map.tsx, show-staff.tsx, etc.) keeps working
// unchanged — token storage itself now lives solely in tokenStorage.ts.
export { getAccessToken };

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user_id: string;
  expires_in: number;
  finish_profile_prompt?: boolean;
};

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });

  await saveAccessToken(response.access_token);

  return response;
}

export async function register(
  full_name: string,
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await request<LoginResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name,
      email,
      password,
    }),
  });

  await saveAccessToken(response.access_token);

  return response;
}

export async function logout() {
  const token = await getAccessToken();

  if (token) {
    try {
      await request("/auth/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.warn("Logout request failed", error);
    }
  }

  await clearAccessToken();
}

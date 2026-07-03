import * as SecureStore from "expo-secure-store";
import { request } from "./api";

const ACCESS_TOKEN_KEY = "access_token";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user_id: string;
  expires_in: number;
  finish_profile_prompt?: boolean;
};

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response =
    await request<LoginResponse>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      }
    );

  await SecureStore.setItemAsync(
    ACCESS_TOKEN_KEY,
    response.access_token
  );

  return response;
}

export async function register(
  full_name: string,
  email: string,
  password: string
): Promise<LoginResponse> {
  const response =
    await request<LoginResponse>(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify({
          full_name,
          email,
          password,
        }),
      }
    );

  await SecureStore.setItemAsync(
    ACCESS_TOKEN_KEY,
    response.access_token
  );

  return response;
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(
    ACCESS_TOKEN_KEY
  );
}

export async function logout() {
  const token =
    await getAccessToken();

  if (token) {
    try {
      await request(
        "/auth/logout",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
    } catch (error) {
      console.warn(
        "Logout request failed",
        error
      );
    }
  }

  await SecureStore.deleteItemAsync(
    ACCESS_TOKEN_KEY
  );
}
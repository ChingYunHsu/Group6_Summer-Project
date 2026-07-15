import { saveAuthData } from "./tokenStorage";

async function authRequest(endpoint, payload) {
  const response = await fetch(`/api/v1/auth/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });

  if (!response.ok) {
    const text = await response.text();

    let parsedBody = null;

    try {
      parsedBody = JSON.parse(text);
    } catch {
      parsedBody = null;
    }

    const error = new Error(
      parsedBody?.error || `Auth request failed: ${response.status}. ${text}`
    );

    error.status = response.status;
    error.body = parsedBody;

    throw error;
  }

  const data = await response.json();

  saveAuthData(data);

  return data;
}

export function login(email, password) {
  return authRequest("login", {
    email,
    password,
  });
}

export function register(fullName, email, password) {
  return authRequest("register", {
    full_name: fullName,
    email,
    password,
  });
}

export function guestLogin() {
  return authRequest("guest");
}
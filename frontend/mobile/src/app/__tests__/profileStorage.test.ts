import * as SecureStore from "expo-secure-store";

import {
    loadProfile,
    saveProfile,
} from "../../services/profileService";

jest.mock("expo-secure-store", () => ({
  setItemAsync: jest.fn(),
  getItemAsync: jest.fn(),
}));

describe("profileStorage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("saves profile data to SecureStore", async () => {
    const profile = {
      user_id: "u_1001",
      full_name: "Amelia Rivera",
      email: "amelia.rivera@example.com",
      phone: "+1 (917) 555-0118",
    };

    await saveProfile(profile);

    expect(
      SecureStore.setItemAsync
    ).toHaveBeenCalledWith(
      "medical_profile",
      JSON.stringify(profile)
    );
  });

  it("loads profile data from SecureStore", async () => {
    const profile = {
      user_id: "u_1001",
      full_name: "Amelia Rivera",
      email: "amelia.rivera@example.com",
      phone: "+1 (917) 555-0118",
    };

    (
      SecureStore.getItemAsync as jest.Mock
    ).mockResolvedValue(
      JSON.stringify(profile)
    );

    const result =
      await loadProfile();

    expect(result).toEqual(profile);

    expect(
      SecureStore.getItemAsync
    ).toHaveBeenCalledWith(
      "medical_profile"
    );
  });

  it("returns null when no profile exists", async () => {
    (
      SecureStore.getItemAsync as jest.Mock
    ).mockResolvedValue(null);

    const result =
      await loadProfile();

    expect(result).toBeNull();

    expect(
      SecureStore.getItemAsync
    ).toHaveBeenCalledWith(
      "medical_profile"
    );
  });
});
import { request } from "../../services/api";
import { loadProfile, saveProfile } from "../../services/profileService";

jest.mock("../../services/api", () => ({
  request: jest.fn(),
}));

const mockedRequest = request as jest.Mock;

describe("profileService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("saves profile data via the API", async () => {
    const responseBody = {
      full_name: "Amelia Rivera",
      user_id: "user-1",
      email: "amelia@example.com",
      phone: "+1 (917) 555-0118",
      nationality: "US",
      spoken_languages: ["en"],
    };

    mockedRequest.mockResolvedValue(responseBody);

    const result = await saveProfile({
      phone: "+1 (917) 555-0118",
      nationality: "US",
      spoken_languages: ["en"],
    });

    expect(mockedRequest).toHaveBeenCalledWith("/user/profile", {
      method: "PUT",
      body: JSON.stringify({
        phone: "+1 (917) 555-0118",
        nationality: "US",
        spoken_languages: ["en"],
      }),
    });

    // profileService maps the backend's `display_name` onto `full_name`
    // for the rest of the app — see mergeProfileResponse.
    expect(result.full_name).toBe("Amelia Rivera");
    expect(result.phone).toBe("+1 (917) 555-0118");
  });

  it("loads profile data via the API", async () => {
    const responseBody = {
      full_name: "Amelia Rivera",
      user_id: "user-1",
      email: "amelia@example.com",
      phone: "+1 (917) 555-0118",
      nationality: "US",
      spoken_languages: ["en"],
    };

    mockedRequest.mockResolvedValue(responseBody);

    const result = await loadProfile();

    expect(mockedRequest).toHaveBeenCalledWith("/user/profile");
    expect(result.full_name).toBe("Amelia Rivera");
    expect(result.phone).toBe("+1 (917) 555-0118");
    expect(result.nationality).toBe("US");
    expect(result.spoken_languages).toEqual(["en"]);
  });

  // A freshly registered account has phone/nationality/spoken_languages
  // as null from the backend (register_user only sets display_name) —
  // mergeProfileResponse should fall back to empty values, not throw or
  // leave them null, since edit-profile.tsx calls .join() on languages.
  it("falls back to empty values for a freshly registered profile", async () => {
    mockedRequest.mockResolvedValue({
      user_id: "user-1",
      email: "new@example.com",
      full_name: "New User",
      phone: null,
      nationality: null,
      spoken_languages: null,
    });

    const result = await loadProfile();

    expect(result.full_name).toBe("New User");
    expect(result.phone).toBe("");
    expect(result.nationality).toBe("");
    expect(result.spoken_languages).toEqual([]);
  });
});

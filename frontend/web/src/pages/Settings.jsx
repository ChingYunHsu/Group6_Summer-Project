import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  deleteAccount,
  getUserProfile,
  updateUserProfile,
} from "../services/UserProfileApi";
import { getMedicalProfile } from "../services/MedicalProfileApi";
import { resetPassword } from "../services/AuthApi";

import "./Settings.css";

const AUTH_MODE_KEY = "auth_mode";
const LOGGED_OUT_MODE = "logged_out";
const LOCATION_SHARING_KEY = "clearPathLocationSharing";

function Settings({
  isAuthenticatedUser = false,
  isGuestUser = false,
  setAuthMode,
  setUser,
}) {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [languagePreference, setLanguagePreference] = useState("");

  const [locationSharing, setLocationSharing] = useState(() => {
    return localStorage.getItem(LOCATION_SHARING_KEY) !== "false";
  });

  const [isLoading, setIsLoading] = useState(isAuthenticatedUser);
  const [isSavingLanguage, setIsSavingLanguage] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [isSendingResetEmail, setIsSendingResetEmail] = useState(false);
  const [passwordModalError, setPasswordModalError] = useState("");
  const [resetEmailSent, setResetEmailSent] = useState(false);

  /*
   * Only authenticated account holders need profile data.
   *
   * Guests and logged-out users must still be able to open the Settings page
   * and read all privacy, security, and legal information.
   */
  useEffect(() => {
    if (!isAuthenticatedUser) {
      setProfile(null);
      setLanguagePreference("");
      setIsLoading(false);
      setError("");
      return;
    }

    let isCancelled = false;

    async function loadSettings() {
      try {
        setIsLoading(true);
        setError("");

        const [userProfile, medicalProfile] = await Promise.all([
          getUserProfile(),
          getMedicalProfile(),
        ]);

        if (isCancelled) {
          return;
        }

        const combinedProfile = {
          ...medicalProfile,
          ...userProfile,
          spoken_languages:
            userProfile?.spoken_languages ??
            medicalProfile?.spoken_languages ??
            [],
        };

        setProfile(combinedProfile);

        setLanguagePreference(
          combinedProfile.spoken_languages?.[0] ?? ""
        );
      } catch (loadError) {
        if (isCancelled) {
          return;
        }

        console.error("Failed to load settings:", loadError);

        setProfile(null);
        setError(
          loadError.message ||
            "Could not load your account settings. Privacy and legal information remains available below."
        );
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadSettings();

    return () => {
      isCancelled = true;
    };
  }, [isAuthenticatedUser]);

  async function handleLanguageChange(event) {
    if (!isAuthenticatedUser || !profile) {
      return;
    }

    const selectedLanguage = event.target.value;
    const previousLanguage = languagePreference;

    setLanguagePreference(selectedLanguage);
    setError("");
    setSuccessMessage("");
    setIsSavingLanguage(true);

    try {
      const existingLanguages = profile.spoken_languages ?? [];

      const updatedLanguages = [
        selectedLanguage,
        ...existingLanguages.filter(
          (language) => language !== selectedLanguage
        ),
      ].filter(Boolean);

      const updatedProfile = await updateUserProfile({
        spoken_languages: updatedLanguages,
      });

      setProfile((currentProfile) => ({
        ...currentProfile,
        ...updatedProfile,
        spoken_languages:
          updatedProfile?.spoken_languages ?? updatedLanguages,
      }));

      setSuccessMessage("Language preference saved.");
    } catch (saveError) {
      console.error("Failed to save language preference:", saveError);

      setLanguagePreference(previousLanguage);

      setError(
        saveError.message ||
          "Could not save your language preference."
      );
    } finally {
      setIsSavingLanguage(false);
    }
  }

  function handleLocationSharingToggle() {
    setLocationSharing((currentValue) => {
      const nextValue = !currentValue;

      localStorage.setItem(
        LOCATION_SHARING_KEY,
        String(nextValue)
      );

      if (!nextValue) {
        localStorage.removeItem("clearPathUserLocation");
      }

      return nextValue;
    });
  }

  function handleChangePassword() {
    if (!isAuthenticatedUser || !profile?.email) {
      return;
    }

    setPasswordModalError("");
    setResetEmailSent(false);
    setIsPasswordModalOpen(true);
  }

  function handleClosePasswordModal() {
    if (isSendingResetEmail) {
      return;
    }

    setIsPasswordModalOpen(false);
    setPasswordModalError("");
    setResetEmailSent(false);
  }

  async function handleSendResetEmail() {
    if (!profile?.email) {
      setPasswordModalError(
        "No registered email address is available for this account."
      );
      return;
    }

    try {
      setIsSendingResetEmail(true);
      setPasswordModalError("");

      /*
       * The endpoint deliberately returns the same success response whether
       * the email exists or not, preventing account enumeration.
       */
      await resetPassword(profile.email);

      setResetEmailSent(true);
    } catch (resetError) {
      console.error("Failed to request password reset:", resetError);

      setPasswordModalError(
        resetError.message || "Could not send the reset email."
      );
    } finally {
      setIsSendingResetEmail(false);
    }
  }

  function clearLocalSession() {
    localStorage.removeItem("clearPathUserLocation");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem(AUTH_MODE_KEY);

    setUser?.(null);
    setAuthMode?.(LOGGED_OUT_MODE);
  }

  function handleLogout() {
    clearLocalSession();
    navigate("/", { replace: true });
  }

  async function handleDeleteAccount() {
    if (!isAuthenticatedUser) {
      return;
    }

    const confirmed = window.confirm(
      "Delete your ClearPath account permanently? This cannot be undone."
    );

    if (!confirmed) {
      return;
    }

    try {
      setIsDeleting(true);
      setError("");
      setSuccessMessage("");

      await deleteAccount();

      clearLocalSession();
      navigate("/", { replace: true });
    } catch (deleteError) {
      console.error("Failed to delete account:", deleteError);

      setError(
        deleteError.message ||
          "Could not delete your account."
      );
    } finally {
      setIsDeleting(false);
    }
  }

  const languages = profile?.spoken_languages ?? [];

  return (
    <main className="settings-page">
      <section className="settings-container">
        <h1>Settings</h1>

        {error && (
          <p
            className="settings-message settings-error"
            role="alert"
          >
            {error}
          </p>
        )}

        {successMessage && (
          <p
            className="settings-message settings-success"
            role="status"
          >
            {successMessage}
          </p>
        )}

        {isAuthenticatedUser ? (
          <section className="settings-card">
            <h2>⚙ Account Settings</h2>

            {isLoading ? (
              <p>Loading account settings...</p>
            ) : profile ? (
              <>
                <div className="settings-two-column">
                  <label>
                    Email Address

                    <input
                      type="email"
                      value={profile.email ?? ""}
                      readOnly
                    />

                    <small>Verified account email</small>
                  </label>

                  <label>
                    Language Preference

                    <select
                      value={languagePreference}
                      onChange={handleLanguageChange}
                      disabled={
                        isSavingLanguage || languages.length === 0
                      }
                    >
                      {languages.length > 0 ? (
                        languages.map((language) => (
                          <option
                            key={language}
                            value={language}
                          >
                            {language}
                          </option>
                        ))
                      ) : (
                        <option value="">
                          No languages added
                        </option>
                      )}
                    </select>

                    {isSavingLanguage && <small>Saving...</small>}
                  </label>
                </div>

                <div className="password-box">
                  <div
                    className="password-icon"
                    aria-hidden="true"
                  >
                    🔒
                  </div>

                  <div>
                    <strong>Security Password</strong>
                    <p>Manage the password for your account.</p>
                  </div>

                  <button
                    type="button"
                    onClick={handleChangePassword}
                  >
                    Change Password
                  </button>
                </div>

                <div className="logout-box">
                  <div>
                    <strong>Session</strong>
                    <p>Log out of your current ClearPath session.</p>
                  </div>

                  <button
                    type="button"
                    onClick={handleLogout}
                  >
                    Log Out
                  </button>
                </div>
              </>
            ) : (
              <p>
                Your account settings could not be loaded. Privacy and
                legal information remains available below.
              </p>
            )}
          </section>
        ) : (
          <section className="settings-card">
            <h2>Guest Access</h2>

            <p>
              {isGuestUser
                ? "You are currently using ClearPath as a guest."
                : "You are not currently signed in."}
            </p>

            <p>
              Privacy, security, location, and legal information remains
              available without an account. Sign in to manage profile,
              password, language, and account-deletion settings.
            </p>

            <button
              type="button"
              onClick={() => navigate("/")}
            >
              Login / Register
            </button>
          </section>
        )}

        {/*
         * This entire section is intentionally public.
         * Do not place it inside an authenticated-user condition.
         */}
        <section className="settings-card">
          <h2>▣ Privacy &amp; Security</h2>

          <div className="privacy-grid">
            <div className="location-box">
              <div className="privacy-top-row">
                <strong>Location Sharing</strong>

                <button
                  className={
                    locationSharing
                      ? "toggle active"
                      : "toggle"
                  }
                  type="button"
                  onClick={handleLocationSharingToggle}
                  aria-label={
                    locationSharing
                      ? "Disable location sharing"
                      : "Enable location sharing"
                  }
                  aria-pressed={locationSharing}
                />
              </div>

              <p>
                Allow ClearPath to use your GPS location to initialise
                the map and calculate nearby healthcare routes.
              </p>

              <p>
                Location permission is controlled by both this preference
                and your browser settings. Disabling it removes the saved
                ClearPath location from this browser.
              </p>

              <a href="#privacy-policy">
                Read how location information is handled
              </a>
            </div>

            <div className="legal-box">
              <strong>Legal Documents</strong>

              <a href="#privacy-policy">
                Privacy Policy <span aria-hidden="true">↓</span>
              </a>

              <a href="#terms-of-service">
                Terms of Service <span aria-hidden="true">↓</span>
              </a>
            </div>
          </div>
        </section>

        <section
          id="privacy-policy"
          className="settings-card"
        >
          <h2>Privacy Policy</h2>

          <h3>Information ClearPath may process</h3>

          <p>
            ClearPath may process information that you provide directly,
            including account details, profile preferences, medical-profile
            information, accessibility needs, saved facilities, and reports
            submitted through the service.
          </p>

          <p>
            When location access is enabled, ClearPath may process your
            approximate or precise device location to display nearby
            facilities and calculate routes. Location access can be disabled
            through this page or through your browser permissions.
          </p>

          <h3>How information is used</h3>

          <p>
            Information is used to provide account features, personalise
            accessibility and language preferences, locate relevant
            facilities, display safety information, maintain service
            security, and investigate technical or misuse reports.
          </p>

          <h3>Medical and sensitive information</h3>

          <p>
            Medical information should only be added when you choose to use
            the medical-profile or medical-card features. Do not rely on
            ClearPath as a replacement for professional medical advice,
            diagnosis, treatment, or emergency services.
          </p>

          <h3>Sharing and disclosure</h3>

          <p>
            ClearPath should not disclose personal information to unrelated
            third parties except where needed to operate an authorised
            service, comply with legal obligations, protect users and the
            public, or act with the user&apos;s permission.
          </p>

          <h3>Security</h3>

          <p>
            ClearPath uses technical and organisational controls intended to
            protect account and medical information. No online system can
            guarantee absolute security, so users should protect their
            passwords and immediately report suspected unauthorised access.
          </p>

          <h3>Your choices</h3>

          <p>
            Registered users can review and update supported profile
            information, change security credentials, manage location
            permission, and request account deletion. Guests can use public
            map, settings, privacy, and legal information without creating a
            registered account.
          </p>
        </section>

        <section
          id="terms-of-service"
          className="settings-card"
        >
          <h2>Terms of Service</h2>

          <h3>Use of the service</h3>

          <p>
            ClearPath provides informational navigation, accessibility, and
            healthcare-facility discovery tools. You may use the service only
            for lawful purposes and must not interfere with its operation,
            security, or other users.
          </p>

          <h3>No emergency-service guarantee</h3>

          <p>
            ClearPath is not an emergency dispatch service. In an emergency,
            contact the appropriate local emergency service immediately.
            Facility availability, opening hours, routes, accessibility data,
            busyness estimates, and travel times may be incomplete, delayed,
            or inaccurate.
          </p>

          <h3>Account responsibility</h3>

          <p>
            Registered users are responsible for maintaining the
            confidentiality of their sign-in credentials and for activity
            performed through their accounts. Information entered into a
            profile should be accurate and should not unlawfully identify or
            expose another person.
          </p>

          <h3>Guest sessions</h3>

          <p>
            Guest access may provide fewer account features and may not
            preserve preferences or information in the same way as a
            registered account. Guests can still access Settings, the Privacy
            Policy, the Terms of Service, and relevant security information.
          </p>

          <h3>Service changes</h3>

          <p>
            ClearPath features may change as the service is developed.
            Functions may be added, modified, temporarily unavailable, or
            discontinued when necessary for security, maintenance, or product
            development.
          </p>
        </section>

        {isAuthenticatedUser && profile && (
          <section className="settings-card danger-card">
            <div className="danger-label">
              ⚠ DANGER ZONE
            </div>

            <div className="danger-panel">
              <h3>Delete Account</h3>

              <p>
                Once deleted, your profile, saved locations, and medical
                information cannot be recovered.
              </p>

              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={isDeleting}
              >
                {isDeleting
                  ? "Deleting Account..."
                  : "🗑 Delete Account & Erase All Data"}
              </button>
            </div>
          </section>
        )}

        <footer className="settings-footer">
          <p>ClearPath Preview App v0.1.0-alpha</p>
          <p>
            © 2026 DataHealth Intelligence. All Rights Reserved.
          </p>
        </footer>
      </section>

      {isAuthenticatedUser &&
        profile?.email &&
        isPasswordModalOpen && (
          <div
            role="presentation"
            onClick={handleClosePasswordModal}
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(0, 0, 0, 0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
            }}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="change-password-title"
              onClick={(event) => event.stopPropagation()}
              style={{
                backgroundColor: "#fff",
                borderRadius: "8px",
                padding: "24px",
                width: "100%",
                maxWidth: "400px",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.2)",
              }}
            >
              <h2
                id="change-password-title"
                style={{ marginTop: 0 }}
              >
                Change Password
              </h2>

              {resetEmailSent ? (
                <>
                  <p>
                    If an account exists for{" "}
                    <strong>{profile.email}</strong>, we&apos;ve sent a
                    link to reset your password. Check your inbox to
                    continue.
                  </p>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                    }}
                  >
                    <button
                      type="button"
                      onClick={handleClosePasswordModal}
                    >
                      Done
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p>
                    We&apos;ll send a password-reset link to your
                    registered email address,{" "}
                    <strong>{profile.email}</strong>.
                  </p>

                  {passwordModalError && (
                    <p
                      role="alert"
                      style={{
                        color: "#b00020",
                        marginBottom: "12px",
                      }}
                    >
                      {passwordModalError}
                    </p>
                  )}

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: "8px",
                    }}
                  >
                    <button
                      type="button"
                      onClick={handleClosePasswordModal}
                      disabled={isSendingResetEmail}
                    >
                      Cancel
                    </button>

                    <button
                      type="button"
                      onClick={handleSendResetEmail}
                      disabled={isSendingResetEmail}
                    >
                      {isSendingResetEmail
                        ? "Sending..."
                        : "Send Reset Email"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
    </main>
  );
}

export default Settings;
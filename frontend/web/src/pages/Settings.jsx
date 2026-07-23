import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getUserProfile,
  updateUserProfile,
  deleteAccount,
} from "../services/UserProfileApi";
import { getMedicalProfile } from "../services/MedicalProfileApi";
import { resetPassword } from "../services/AuthApi";
import "./Settings.css";

function Settings() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [languagePreference, setLanguagePreference] = useState("");

  const [locationSharing, setLocationSharing] = useState(true);

  const [isLoading, setIsLoading] = useState(true);
  const [isSavingLanguage, setIsSavingLanguage] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [isSendingResetEmail, setIsSendingResetEmail] = useState(false);
  const [passwordModalError, setPasswordModalError] = useState("");
  const [resetEmailSent, setResetEmailSent] = useState(false);

  useEffect(() => {
    async function loadSettings() {
      try {
        setIsLoading(true);
        setError("");

        const [userProfile, medicalProfile] = await Promise.all([
          getUserProfile(),
          getMedicalProfile(),
        ]);

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
        console.error("Failed to load settings:", loadError);

        setError(
          loadError.message ||
            "Could not load your account settings."
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadSettings();
  }, []);

  async function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    const previousLanguage = languagePreference;

    setLanguagePreference(selectedLanguage);
    setError("");
    setSuccessMessage("");
    setIsSavingLanguage(true);

    try {
      /*
       * Your profile endpoint currently accepts spoken_languages.
       * Preserve all existing languages but move the selected preference
       * to the beginning of the array.
       */
      const existingLanguages = profile?.spoken_languages ?? [];

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

  function handleChangePassword() {
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
    try {
      setIsSendingResetEmail(true);
      setPasswordModalError("");

      // Per the API contract, this endpoint always responds success
      // whether or not the address is registered (anti-enumeration),
      // so we show the same confirmation regardless of the response body.
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

  function handleLogout() {
    localStorage.removeItem("clearPathUserLocation");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");

    navigate("/");
  }

  async function handleDeleteAccount() {
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

      localStorage.removeItem("clearPathUserLocation");
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");

      navigate("/");
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

  if (isLoading) {
    return (
      <main className="settings-page">
        <section className="settings-container">
          <p>Loading settings...</p>
        </section>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="settings-page">
        <section className="settings-container">
          <h1>Settings</h1>
          <p role="alert">{error || "Profile unavailable."}</p>
        </section>
      </main>
    );
  }

  const languages = profile.spoken_languages ?? [];

  return (
    <main className="settings-page">
      <section className="settings-container">
        <h1>Settings</h1>

        {error && (
          <p className="settings-message settings-error" role="alert">
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

        <section className="settings-card">
          <h2>⚙ Account Settings</h2>

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
                    <option key={language} value={language}>
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
            <div className="password-icon">🔒</div>

            <div>
              <strong>Security Password</strong>
              <p>Manage the password for your account.</p>
            </div>

            <button type="button" onClick={handleChangePassword}>
              Change Password
            </button>
          </div>

          <div className="logout-box">
            <div>
              <strong>Session</strong>
              <p>Log out of your current ClearPath session.</p>
            </div>

            <button type="button" onClick={handleLogout}>
              Log Out
            </button>
          </div>
        </section>

        <section className="settings-card">
          <h2>▣ Privacy & Security</h2>

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
                  onClick={() =>
                    setLocationSharing((current) => !current)
                  }
                  aria-label="Toggle location sharing"
                  aria-pressed={locationSharing}
                />
              </div>

              <p>
                Allow ClearPath to use your GPS to provide
                local facility routing.
              </p>

              <a href="#privacy-information">
                Data is anonymized before transmission.
              </a>
            </div>

            <div className="legal-box">
              <strong>Legal Documents</strong>

              <button
                type="button"
                onClick={() => navigate("/privacy-policy")}
              >
                Privacy Policy <span>↗</span>
              </button>

              <button
                type="button"
                onClick={() => navigate("/terms")}
              >
                Terms of Service <span>↗</span>
              </button>
            </div>
          </div>
        </section>

        <section className="settings-card danger-card">
          <div className="danger-label">⚠ DANGER ZONE</div>

          <div className="danger-panel">
            <h3>Delete Account</h3>

            <p>
              Once deleted, your profile, saved locations, and
              medical information cannot be recovered.
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

        <footer className="settings-footer">
          <p>ClearPath Preview App v0.1.0-alpha</p>
          <p>© 2026 DataHealth Intelligence. All Rights Reserved.</p>
        </footer>
      </section>

      {isPasswordModalOpen && (
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
            <h2 id="change-password-title" style={{ marginTop: 0 }}>
              Change Password
            </h2>

            {resetEmailSent ? (
              <>
                <p>
                  If an account exists for <strong>{profile.email}</strong>,
                  we've sent a link to reset your password. Check your
                  inbox to continue.
                </p>

                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button type="button" onClick={handleClosePasswordModal}>
                    Done
                  </button>
                </div>
              </>
            ) : (
              <>
                <p>
                  We'll send a password reset link to your registered
                  email address, <strong>{profile.email}</strong>.
                </p>

                {passwordModalError && (
                  <p
                    role="alert"
                    style={{ color: "#b00020", marginBottom: "12px" }}
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
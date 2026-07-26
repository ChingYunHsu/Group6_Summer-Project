import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation("common");

  const [profile, setProfile] = useState(null);
  const [languagePreference, setLanguagePreference] = useState("");

  const [locationSharing, setLocationSharing] = useState(() => {
    return localStorage.getItem(LOCATION_SHARING_KEY) !== "false";
  });

 const [error, setError] = useState("");
const [successMessage, setSuccessMessage] = useState("");

const isLoading =
  isAuthenticatedUser &&
  profile === null &&
  error === "";

const [isSavingLanguage, setIsSavingLanguage] = useState(false);
const [isDeleting, setIsDeleting] = useState(false);

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
    return;
  }

  let isCancelled = false;

  async function loadSettings() {
    try {
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
      setError("");
    } catch (loadError) {
      if (isCancelled) {
        return;
      }

      console.error("Failed to load settings:", loadError);

      setProfile(null);
      setError(
        loadError.message ||
          t("settings.couldNotLoadSettings")
      );
    }
  }

  loadSettings();

  return () => {
    isCancelled = true;
  };
}, [isAuthenticatedUser, t]);

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

      setSuccessMessage(t("settings.languageSaved"));
    } catch (saveError) {
      console.error("Failed to save language preference:", saveError);

      setLanguagePreference(previousLanguage);

      setError(
        saveError.message ||
          t("settings.couldNotSaveLanguage")
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
      setPasswordModalError(t("settings.noRegisteredEmail"));
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
        resetError.message || t("settings.couldNotSendResetEmail")
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

  function handleOpenGuideSection(sectionId) {
    navigate(`/guide?section=${sectionId}`);
  }

  async function handleDeleteAccount() {
    if (!isAuthenticatedUser) {
      return;
    }

    const confirmed = window.confirm(t("settings.confirmDeleteAccount"));

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
          t("settings.couldNotDeleteAccount")
      );
    } finally {
      setIsDeleting(false);
    }
  }

  const languages = profile?.spoken_languages ?? [];

  return (
    <main className="settings-page">
      <section className="settings-container">
        <h1>{t("settings.title")}</h1>

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
            <h2>⚙ {t("settings.accountSettings")}</h2>

            {isLoading ? (
              <p>{t("settings.loadingAccountSettings")}</p>
            ) : profile ? (
              <>
                <div className="settings-two-column">
                  <label>
                    {t("login.emailAddress")}

                    <input
                      type="email"
                      value={profile.email ?? ""}
                      readOnly
                    />

                    <small>{t("settings.verifiedAccountEmail")}</small>
                  </label>

                  <label>
                    {t("settings.languagePreference")}

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
                          {t("settings.noLanguagesAdded")}
                        </option>
                      )}
                    </select>

                    {isSavingLanguage && <small>{t("common.saving")}</small>}
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
                    <strong>{t("settings.securityPassword")}</strong>
                    <p>{t("settings.managePasswordDescription")}</p>
                  </div>

                  <button
                    type="button"
                    onClick={handleChangePassword}
                  >
                    {t("settings.changePassword")}
                  </button>
                </div>

                <div className="logout-box">
                  <div>
                    <strong>{t("settings.session")}</strong>
                    <p>{t("settings.logoutDescription")}</p>
                  </div>

                  <button
                    type="button"
                    onClick={handleLogout}
                  >
                    {t("settings.logout")}
                  </button>
                </div>
              </>
            ) : (
              <p>
                {t("settings.settingsUnavailable")}
              </p>
            )}
          </section>
        ) : (
          <section className="settings-card">
            <h2>{t("settings.guestAccess")}</h2>

            <p>
              {isGuestUser
                ? t("settings.guestAccessDescriptionGuest")
                : t("settings.guestAccessDescriptionLoggedOut")}
            </p>

            <p>
              {t("settings.guestAccessBody")}
            </p>

            <button
              type="button"
              onClick={() => navigate("/")}
            >
              {t("settings.loginRegisterCta")}
            </button>
          </section>
        )}

        {/*
         * This entire section is intentionally public.
         * Do not place it inside an authenticated-user condition.
         */}
        <section className="settings-card">
          <h2>▣ {t("settings.privacySecurity")}</h2>

          <div className="privacy-grid">
            <div className="location-box">
              <div className="privacy-top-row">
                <strong>{t("settings.locationSharing")}</strong>

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
                      ? t("settings.disableLocationSharing")
                      : t("settings.enableLocationSharing")
                  }
                  aria-pressed={locationSharing}
                />
              </div>

              <p>
                {t("settings.locationSharingDescription")}
              </p>

              <p>
                {t("settings.locationSharingHelper")}
              </p>

              <button
                type="button"
                className="settings-link-button"
                onClick={() =>
                  handleOpenGuideSection("privacy-policy")
                }
              >
                {t("settings.readLocationHandling")}
              </button>
            </div>

            <div className="legal-box">
              <strong>{t("settings.legalDocuments")}</strong>

              <button
                type="button"
                className="settings-link-button legal-document-button"
                onClick={() =>
                  handleOpenGuideSection("privacy-policy")
                }
              >
                <span>{t("settings.privacyPolicy")}</span>
                <span aria-hidden="true">→</span>
              </button>

              <button
                type="button"
                className="settings-link-button legal-document-button"
                onClick={() =>
                  handleOpenGuideSection("terms")
                }
              >
                <span>{t("settings.termsOfService")}</span>
                <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        </section>


        {isAuthenticatedUser && profile && (
          <section className="settings-card danger-card">
            <div className="danger-label">
              ⚠ {t("settings.dangerZone")}
            </div>

            <div className="danger-panel">
              <h3>{t("settings.deleteAccountTitle")}</h3>

              <p>
                {t("settings.deleteAccountBody")}
              </p>

              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={isDeleting}
              >
                {isDeleting
                  ? t("settings.deletingAccount")
                  : t("settings.deleteAccountCta")}
              </button>
            </div>
          </section>
        )}

        <footer className="settings-footer">
          <p>{t("settings.footerAppVersion")}</p>
          <p>
            {t("settings.footerCopyright")}
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
                {t("settings.changePasswordTitle")}
              </h2>

              {resetEmailSent ? (
                <>
                  <p>
                    {t("settings.resetEmailSentMessage", {
                      email: profile.email,
                    })}
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
                      {t("common.done")}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p>
                    {t("settings.resetEmailIntro", {
                      email: profile.email,
                    })}
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
                      {t("common.cancel")}
                    </button>

                    <button
                      type="button"
                      onClick={handleSendResetEmail}
                      disabled={isSendingResetEmail}
                    >
                      {isSendingResetEmail
                        ? t("settings.sendingResetEmail")
                        : t("settings.sendResetEmail")}
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

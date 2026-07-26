import {
  useEffect,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import clearPathLogo from "../assets/clearpath-logo.png";
import loginPeopleImage from "../assets/login-people.jpg";

import "./Login.css";

import {
  guestLogin,
  login,
  register,
} from "../services/authService";

const AUTH_MODE_KEY = "auth_mode";
const AUTHENTICATED_MODE = "authenticated";
const GUEST_MODE = "guest";

function Login({
  setUserLocation,
  setUser,
  setAuthMode,
}) {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  const [
    showLocationModal,
    setShowLocationModal,
  ] = useState(false);

  const [
    showProfileIntercept,
    setShowProfileIntercept,
  ] = useState(false);

  const [
    locationError,
    setLocationError,
  ] = useState("");

  const [
    isRequestingLocation,
    setIsRequestingLocation,
  ] = useState(false);

  const [
    isRegister,
    setIsRegister,
  ] = useState(false);

  const [
    isAuthenticating,
    setIsAuthenticating,
  ] = useState(false);

  const [loginForm, setLoginForm] =
    useState({
      email: "",
      password: "",
    });

  const [
    registerForm,
    setRegisterForm,
  ] = useState({
    fullName: "",
    email: "",
    password: "",
  });

  /*
   * Registered users who reach "/" should return to the map.
   * Guest users are allowed to return to login/register.
   */
  useEffect(() => {
    const accessToken =
      localStorage.getItem("access_token");

    const storedAuthMode =
      localStorage.getItem(AUTH_MODE_KEY);

    const isAuthenticatedUser =
      Boolean(accessToken) &&
      storedAuthMode === AUTHENTICATED_MODE;

    if (isAuthenticatedUser) {
      navigate("/map", {
        replace: true,
      });
    }
  }, [navigate]);

  function openLocationModal() {
    setLocationError("");
    setShowLocationModal(true);
  }

  function setAuthenticatedSession(data) {
    localStorage.setItem(
      AUTH_MODE_KEY,
      AUTHENTICATED_MODE
    );

    setAuthMode?.(AUTHENTICATED_MODE);

    setUser?.(
      data?.user ?? {
        authMode: AUTHENTICATED_MODE,
      }
    );
  }

  function setGuestSession(data) {
    localStorage.setItem(
      AUTH_MODE_KEY,
      GUEST_MODE
    );

    setAuthMode?.(GUEST_MODE);

    setUser?.({
      authMode: GUEST_MODE,
      userId: data?.user_id ?? null,
    });
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();

    if (
      !loginForm.email ||
      !loginForm.password
    ) {
      alert(t("login.emailPasswordRequired"));
      return;
    }

    try {
      setIsAuthenticating(true);

      const data = await login(
        loginForm.email,
        loginForm.password
      );

      setAuthenticatedSession(data);
      openLocationModal();
    } catch (error) {
      console.error(
        "Login request failed:",
        error
      );

      const problemFields = [
        ...(error?.body?.missing_fields ??
          []),
        ...(error?.body?.invalid_fields ??
          []),
      ];

      const message =
        problemFields.length > 0
          ? `${error.message} (${problemFields.join(
              ", "
            )})`
          : error.message ||
            t("login.signInErrorMessage");

      alert(message);
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function handleRegisterSubmit(
    event
  ) {
    event.preventDefault();

    if (
      !registerForm.fullName ||
      !registerForm.email ||
      !registerForm.password
    ) {
      alert(t("login.registrationFieldsRequired"));
      return;
    }

    if (
      registerForm.password.length < 8
    ) {
      alert(t("login.passwordTooShort"));
      return;
    }

    try {
      setIsAuthenticating(true);

      const data = await register(
        registerForm.fullName,
        registerForm.email,
        registerForm.password
      );

      setAuthenticatedSession(data);

      if (data.finish_profile_prompt) {
        setShowProfileIntercept(true);
      } else {
        openLocationModal();
      }
    } catch (error) {
      console.error(
        "Register request failed:",
        error
      );

      const problemFields = [
        ...(error?.body?.missing_fields ??
          []),
        ...(error?.body?.invalid_fields ??
          []),
      ];

      const message =
        problemFields.length > 0
          ? `${error.message} (${problemFields.join(
              ", "
            )})`
          : error.message ||
            t("login.registerErrorMessage");

      alert(message);
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function handleGuestContinue() {
    try {
      setIsAuthenticating(true);

      const data = await guestLogin();

      setGuestSession(data);
      openLocationModal();
    } catch (error) {
      console.error(
        "Guest session request failed:",
        error
      );

      alert(
        error.message ||
          t("login.couldNotStartGuestSession")
      );
    } finally {
      setIsAuthenticating(false);
    }
  }

  function handleFinishProfile() {
    setShowProfileIntercept(false);
    navigate("/profile/edit");
  }

  function handleSkipProfile() {
    setShowProfileIntercept(false);
    openLocationModal();
  }

  function handleAllowAccess() {
    setLocationError("");

    if (!navigator.geolocation) {
      setLocationError(t("login.geolocationUnsupported"));
      return;
    }

    setIsRequestingLocation(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const userLocation = {
          latitude:
            position.coords.latitude,
          longitude:
            position.coords.longitude,
        };

        setUserLocation?.(userLocation);

        localStorage.setItem(
          "clearPathUserLocation",
          JSON.stringify(userLocation)
        );

        setIsRequestingLocation(false);
        setShowLocationModal(false);

        navigate("/map");
      },
      () => {
        setIsRequestingLocation(false);

        setLocationError(t("login.locationDenied"));
      }
    );
  }

  function handleNotNow() {
    setShowLocationModal(false);
    navigate("/map");
  }

  return (
    <main className="login-page">
      <section
        className="login-brand-panel"
        style={{
          backgroundImage: `url(${loginPeopleImage})`,
        }}
      >
        <div className="brand-content">
          <div>
            <img
              src={clearPathLogo}
              alt=""
              aria-hidden="true"
              className="login-brand-logo"
            />

            <h1>{t("login.brandName")}</h1>
          </div>

          <div className="brand-line"></div>

          <h2>{t("login.brandTagline")}</h2>

          <p>{t("login.brandDescription")}</p>
        </div>
      </section>

      <section className="login-form-panel">
        <div className="auth-card">
          <div className="auth-tabs">
            <button
              type="button"
              className={
                isRegister ? "" : "active"
              }
              onClick={() =>
                setIsRegister(false)
              }
              disabled={isAuthenticating}
            >
              {t("login.loginTab")}
            </button>

            <button
              type="button"
              className={
                isRegister ? "active" : ""
              }
              onClick={() =>
                setIsRegister(true)
              }
              disabled={isAuthenticating}
            >
              {t("login.registerTab")}
            </button>
          </div>

          {!isRegister ? (
            <form
              onSubmit={handleLoginSubmit}
            >
              <label htmlFor="login-email">
                {t("login.emailAddress")}
              </label>

              <input
                id="login-email"
                type="email"
                placeholder={t("login.emailPlaceholder")}
                autoComplete="email"
                value={loginForm.email}
                onChange={(event) =>
                  setLoginForm({
                    ...loginForm,
                    email:
                      event.target.value,
                  })
                }
              />

              <div className="password-row">
                <label htmlFor="login-password">
                  {t("login.password")}
                </label>

                <a href="#">
                  {t("login.forgotPassword")}
                </a>
              </div>

              <input
                id="login-password"
                type="password"
                placeholder={t("login.passwordPlaceholder")}
                autoComplete="current-password"
                value={loginForm.password}
                onChange={(event) =>
                  setLoginForm({
                    ...loginForm,
                    password:
                      event.target.value,
                  })
                }
              />

              <button
                className="primary-auth-button"
                type="submit"
                disabled={
                  isAuthenticating
                }
              >
                {isAuthenticating
                  ? t("login.signingIn")
                  : t("login.signInCta")}
              </button>
            </form>
          ) : (
            <form
              onSubmit={
                handleRegisterSubmit
              }
            >
              <p className="register-title">
                {t("login.getStarted")}
              </p>

              <p className="hipaa-label">
                {t("login.hipaaSetup")}
              </p>

              <label htmlFor="register-name">
                {t("login.fullName")}
              </label>

              <input
                id="register-name"
                type="text"
                placeholder={t("login.fullNamePlaceholder")}
                autoComplete="name"
                value={
                  registerForm.fullName
                }
                onChange={(event) =>
                  setRegisterForm({
                    ...registerForm,
                    fullName:
                      event.target.value,
                  })
                }
              />

              <label htmlFor="register-email">
                {t("login.emailAddress")}
              </label>

              <input
                id="register-email"
                type="email"
                placeholder={t("login.emailPlaceholder")}
                autoComplete="email"
                value={registerForm.email}
                onChange={(event) =>
                  setRegisterForm({
                    ...registerForm,
                    email:
                      event.target.value,
                  })
                }
              />

              <label htmlFor="register-password">
                {t("login.createPassword")}
              </label>

              <input
                id="register-password"
                type="password"
                placeholder={t("login.passwordRequirements")}
                autoComplete="new-password"
                value={
                  registerForm.password
                }
                onChange={(event) =>
                  setRegisterForm({
                    ...registerForm,
                    password:
                      event.target.value,
                  })
                }
              />

              <p className="hipaa-label">
                {t("login.hipaaLocalFirst")}
              </p>

              <button
                className="primary-auth-button"
                type="submit"
                disabled={
                  isAuthenticating
                }
              >
                {isAuthenticating
                  ? t("login.creatingAccount")
                  : t("login.createAccountCta")}
              </button>
            </form>
          )}

          <div className="divider">
            <span></span>
            <p>{t("login.orDivider")}</p>
            <span></span>
          </div>

          <button
            className="guest-button"
            type="button"
            onClick={
              handleGuestContinue
            }
            disabled={isAuthenticating}
          >
            {isAuthenticating
              ? t("login.startingSession")
              : t("authGateway.continueGuest")}
          </button>

          <p className="terms">
            {t("login.termsAgreement")}
          </p>
        </div>
      </section>

      {showProfileIntercept && (
        <div className="intercept-overlay">
          <div className="intercept-sheet">
            <h2>
              {t("login.profileInterceptTitle")}
            </h2>

            <p>
              {t("login.profileInterceptBody")}
            </p>

            <div className="intercept-actions">
              <button
                type="button"
                onClick={
                  handleSkipProfile
                }
              >
                {t("login.skipForNow")}
              </button>

              <button
                type="button"
                onClick={
                  handleFinishProfile
                }
              >
                {t("login.finishProfile")}
              </button>
            </div>
          </div>
        </div>
      )}

      {showLocationModal && (
        <div className="location-overlay">
          <div className="location-modal">
            <div className="location-icon">
              ⌖
            </div>

            <h2>{t("login.enableLocationTitle")}</h2>

            <p>
              {t("login.enableLocationBody")}
            </p>

            {locationError && (
              <p className="location-error">
                {locationError}
              </p>
            )}

            <div className="location-actions">
              <button
                className="cancel-location-button"
                type="button"
                onClick={handleNotNow}
                disabled={
                  isRequestingLocation
                }
              >
                {t("login.notNow")}
              </button>

              <button
                className="allow-location-button"
                type="button"
                onClick={
                  handleAllowAccess
                }
                disabled={
                  isRequestingLocation
                }
              >
                {isRequestingLocation
                  ? t("login.requestingLocation")
                  : t("login.allowAccess")}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default Login;

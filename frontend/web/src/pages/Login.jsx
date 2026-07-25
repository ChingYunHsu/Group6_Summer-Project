import {
  useEffect,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

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
      alert(
        "Please enter your email and password."
      );
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
            "Please check your details and try again.";

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
      alert(
        "Please complete all registration fields."
      );
      return;
    }

    if (
      registerForm.password.length < 8
    ) {
      alert(
        "Password must be at least 8 characters."
      );
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
            "Please check your details and try again.";

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
          "Could not start a guest session."
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
      setLocationError(
        "Geolocation is not supported by this browser."
      );
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

        setLocationError(
          "Location access was denied. You can continue, but route planning may be limited."
        );
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
          <div className="login-brand-title">
            <img
              src={clearPathLogo}
              alt=""
              aria-hidden="true"
              className="login-brand-logo"
            />

            <h1>ClearPath</h1>
          </div>

          <div className="brand-line"></div>

          <h2>
            Your Safety, Our Priority.
          </h2>

          <p>
            Join our community-driven
            healthcare intelligence network.
            Access real-time insights,
            manage your data securely, and
            navigate your wellness journey
            with absolute clarity.
          </p>
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
              Login
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
              Register
            </button>
          </div>

          {!isRegister ? (
            <form
              onSubmit={handleLoginSubmit}
            >
              <label htmlFor="login-email">
                Email Address
              </label>

              <input
                id="login-email"
                type="email"
                placeholder="name@company.com"
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
                  Password
                </label>

                <a href="#">
                  Forgot Password?
                </a>
              </div>

              <input
                id="login-password"
                type="password"
                placeholder="password"
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
                  ? "Signing in..."
                  : "Sign In to My Account →"}
              </button>
            </form>
          ) : (
            <form
              onSubmit={
                handleRegisterSubmit
              }
            >
              <p className="register-title">
                Get started
              </p>

              <p className="hipaa-label">
                HIPAA-ready protected
                identity asset setup
              </p>

              <label htmlFor="register-name">
                Full Name
              </label>

              <input
                id="register-name"
                type="text"
                placeholder="Enter your full name"
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
                Email Address
              </label>

              <input
                id="register-email"
                type="email"
                placeholder="name@company.com"
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
                Password
              </label>

              <input
                id="register-password"
                type="password"
                placeholder="Create a secure password"
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
                Clinical records remain
                local-first until authorised
                sharing.
              </p>

              <button
                className="primary-auth-button"
                type="submit"
                disabled={
                  isAuthenticating
                }
              >
                {isAuthenticating
                  ? "Creating account..."
                  : "Create Account →"}
              </button>
            </form>
          )}

          <div className="divider">
            <span></span>
            <p>OR</p>
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
              ? "Starting session..."
              : "Continue as Guest"}
          </button>

          <p className="terms">
            By continuing, you agree to
            our Terms of Service and
            Privacy Policy.
          </p>
        </div>
      </section>

      {showProfileIntercept && (
        <div className="intercept-overlay">
          <div className="intercept-sheet">
            <h2>
              Would you like to finish
              setting up your Medical
              Profile and ID now?
            </h2>

            <p>
              Complete your emergency
              medical document now, or
              skip this step and return
              to it later.
            </p>

            <div className="intercept-actions">
              <button
                type="button"
                onClick={
                  handleSkipProfile
                }
              >
                Skip for Now
              </button>

              <button
                type="button"
                onClick={
                  handleFinishProfile
                }
              >
                Finish Profile &amp; ID
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

            <h2>Enable Location</h2>

            <p>
              ClearPath uses your current
              location to initialise the
              map matrix viewport and
              calculate safer healthcare
              routes.
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
                Not Now
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
                  ? "Requesting..."
                  : "Allow Access"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default Login;
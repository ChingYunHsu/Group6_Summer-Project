import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Login.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function Login({ setUserLocation }) {
  const navigate = useNavigate();

  const [showLocationModal, setShowLocationModal] = useState(false);
  const [showProfileIntercept, setShowProfileIntercept] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [isRequestingLocation, setIsRequestingLocation] = useState(false);
  const [isRegister, setIsRegister] = useState(false);

  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  });

  const [registerForm, setRegisterForm] = useState({
    fullName: "",
    email: "",
    password: "",
  });

  function openLocationModal() {
    setLocationError("");
    setShowLocationModal(true);
  }

  function handleLoginSubmit(e) {
    e.preventDefault();

    if (!loginForm.email || !loginForm.password) {
      alert("Please enter your email and password.");
      return;
    }

    openLocationModal();
  }

  async function handleRegisterSubmit(e) {
    e.preventDefault();

    if (!registerForm.fullName || !registerForm.email || !registerForm.password) {
      alert("Please complete all registration fields.");
      return;
    }

    if (registerForm.password.length < 8) {
      alert("Password must be at least 8 characters.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: registerForm.fullName,
          email: registerForm.email,
          password: registerForm.password,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.error || `Registration failed (${res.status}).`);
        return;
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);

      setShowProfileIntercept(true);
    } catch (err) {
      console.error("Register request failed:", err);
      alert("Could not reach the server. Is the backend running?");
    }
  }

  async function handleGuestContinue() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/guest`, {
        method: "POST",
      });

      if (!res.ok) {
        alert("Could not start a guest session.");
        return;
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);

      openLocationModal();
    } catch (err) {
      console.error("Guest session request failed:", err);
      alert("Could not reach the server. Is the backend running?");
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
      setLocationError("Geolocation is not supported by this browser.");
      return;
    }

    setIsRequestingLocation(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const userLocation = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };

        if (setUserLocation) {
          setUserLocation(userLocation);
        }

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
      <section className="login-brand-panel">
        <div className="brand-content">
          <h1>ClearPath</h1>
          <div className="brand-line"></div>
          <h2>Your Safety, Our Priority.</h2>
          <p>
            Join our community-driven healthcare intelligence network. Access
            real-time insights, manage your data securely, and navigate your
            wellness journey with absolute clarity.
          </p>
        </div>
      </section>

      <section className="login-form-panel">
        <div className="auth-card">
          <div className="auth-tabs">
            <button
              type="button"
              className={isRegister ? "" : "active"}
              onClick={() => setIsRegister(false)}
            >
              Login
            </button>

            <button
              type="button"
              className={isRegister ? "active" : ""}
              onClick={() => setIsRegister(true)}
            >
              Register
            </button>
          </div>

          {!isRegister ? (
            <form onSubmit={handleLoginSubmit}>
              <label htmlFor="login-email">Email Address</label>
              <input
                id="login-email"
                type="email"
                placeholder="name@company.com"
                value={loginForm.email}
                onChange={(e) =>
                  setLoginForm({ ...loginForm, email: e.target.value })
                }
              />

              <div className="password-row">
                <label htmlFor="login-password">Password</label>
                <a href="#">Forgot Password?</a>
              </div>

              <input
                id="login-password"
                type="password"
                placeholder="password"
                value={loginForm.password}
                onChange={(e) =>
                  setLoginForm({ ...loginForm, password: e.target.value })
                }
              />

              <button className="primary-auth-button" type="submit">
                Sign In to My Account →
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegisterSubmit}>
              <p className="register-title">Get started</p>

              <p className="hipaa-label">
                HIPAA-ready protected identity asset setup
              </p>

              <label htmlFor="register-name">Full Name</label>
              <input
                id="register-name"
                type="text"
                placeholder="Enter your full name"
                value={registerForm.fullName}
                onChange={(e) =>
                  setRegisterForm({
                    ...registerForm,
                    fullName: e.target.value,
                  })
                }
              />

              <label htmlFor="register-email">Email Address</label>
              <input
                id="register-email"
                type="email"
                placeholder="name@company.com"
                value={registerForm.email}
                onChange={(e) =>
                  setRegisterForm({
                    ...registerForm,
                    email: e.target.value,
                  })
                }
              />

              <label htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                placeholder="Create a secure password"
                value={registerForm.password}
                onChange={(e) =>
                  setRegisterForm({
                    ...registerForm,
                    password: e.target.value,
                  })
                }
              />

              <p className="hipaa-label">
                Clinical records remain local-first until authorised sharing.
              </p>

              <button className="primary-auth-button" type="submit">
                Create Account →
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
            onClick={handleGuestContinue}
          >
            Continue as Guest
          </button>

          <p className="terms">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </section>

      {showProfileIntercept && (
        <div className="intercept-overlay">
          <div className="intercept-sheet">
            <h2>
              Would you like to finish setting up your Medical Profile and ID
              now?
            </h2>
            <p>
              Complete your emergency medical document now, or skip this step and
              return to it later.
            </p>

            <div className="intercept-actions">
              <button type="button" onClick={handleSkipProfile}>
                Skip for Now
              </button>

              <button type="button" onClick={handleFinishProfile}>
                Finish Profile & ID
              </button>
            </div>
          </div>
        </div>
      )}

      {showLocationModal && (
        <div className="location-overlay">
          <div className="location-modal">
            <div className="location-icon">⌖</div>

            <h2>Enable Location</h2>

            <p>
              ClearPath uses your current location to initialise the map matrix
              viewport and calculate safer healthcare routes.
            </p>

            {locationError && <p className="location-error">{locationError}</p>}

            <div className="location-actions">
              <button
                className="cancel-location-button"
                type="button"
                onClick={handleNotNow}
              >
                Not Now
              </button>

              <button
                className="allow-location-button"
                type="button"
                onClick={handleAllowAccess}
                disabled={isRequestingLocation}
              >
                {isRequestingLocation ? "Requesting..." : "Allow Access"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default Login;
import { useState } from "react";
import { useNavigate } from "react-router-dom";

function Login() {
  const navigate = useNavigate();

  const [showLocationModal, setShowLocationModal] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [isRequestingLocation, setIsRequestingLocation] = useState(false);

  function openLocationModal() {
    setLocationError("");
    setShowLocationModal(true);
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

        localStorage.setItem("clearPathUserLocation", JSON.stringify(userLocation));

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

  function handleCancel() {
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
            <button className="active" type="button">
              Login
            </button>
            <button type="button">Register</button>
          </div>

          <label htmlFor="email">Email Address</label>
          <input id="email" type="email" placeholder="name@company.com" />

          <div className="password-row">
            <label htmlFor="password">Password</label>
            <a href="#">Forgot Password?</a>
          </div>

          <input id="password" type="password" placeholder="password" />

          <button
            className="primary-auth-button"
            type="button"
            onClick={openLocationModal}
          >
            Sign In to My Account →
          </button>

          <div className="divider">
            <span></span>
            <p>OR</p>
            <span></span>
          </div>

          <button
            className="guest-button"
            type="button"
            onClick={openLocationModal}
          >
            Continue as Guest
          </button>

          <p className="terms">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </section>

      {showLocationModal && (
        <div className="location-overlay">
          <div className="location-modal">
            <div className="location-icon">⌖</div>

            <h2>Location Access Required</h2>

            <p>
              Location services are required to calculate routes from your
              current position.
            </p>

            {locationError && (
              <p className="location-error">{locationError}</p>
            )}

            <button
              className="allow-location-button"
              type="button"
              onClick={handleAllowAccess}
              disabled={isRequestingLocation}
            >
              {isRequestingLocation ? "Requesting..." : "Allow Access"}
            </button>

            <button
              className="cancel-location-button"
              type="button"
              onClick={handleCancel}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

export default Login;
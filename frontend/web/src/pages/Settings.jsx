import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { USER_PROFILE } from "../data/userProfile";
import "./Settings.css";

function Settings() {
  const navigate = useNavigate();

  const languages = USER_PROFILE.spoken_languages ?? [];

  const [languagePreference, setLanguagePreference] = useState(
    languages[0] || ""
  );

  const [pushNotifications, setPushNotifications] = useState(true);
  const [emailAlerts, setEmailAlerts] = useState(false);
  const [busynessAlerts, setBusynessAlerts] = useState(true);
  const [locationSharing, setLocationSharing] = useState(true);

  function handleChangePassword() {
    alert("Change password flow will be connected later.");
  }

  function handleExportData() {
    alert("Export request initiated. Live export endpoint will be connected later.");
  }

  function handleLogout() {
    localStorage.removeItem("clearPathUserLocation");
    localStorage.removeItem("clearPathMockUser");
    localStorage.removeItem("access_token");

    alert("Mock logout successful. Login integration will be connected later.");

    navigate("/");
  }

  function handleDeleteAccount() {
    alert("Account deletion flow will be connected later.");
  }

  return (
    <main className="settings-page">
      <section className="settings-container">
        <h1>Settings</h1>

        <section className="settings-card">
          <h2>⚙ Account Settings</h2>

          <div className="settings-two-column">
            <label>
              Email Address
              <input value={USER_PROFILE.email} readOnly />
              <small>Verified Professional Account</small>
            </label>

            <label>
              Language Preference
              <select
                value={languagePreference}
                onChange={(event) => setLanguagePreference(event.target.value)}
              >
                {languages.length > 0 ? (
                  languages.map((language) => (
                    <option key={language} value={language}>
                      {language}
                    </option>
                  ))
                ) : (
                  <option value="">No languages added</option>
                )}
              </select>
            </label>
          </div>

          <div className="password-box">
            <div className="password-icon">🔒</div>
            <div>
              <strong>Security Password</strong>
              <p>Last updated 4 months ago</p>
            </div>
            <button type="button" onClick={handleChangePassword}>
              Change Password
            </button>
          </div>

          <div className="logout-box">
            <div>
              <strong>Session</strong>
              <p>Log out of this preview session and return to onboarding.</p>
            </div>

            <button type="button" onClick={handleLogout}>
              Log Out
            </button>
          </div>
        </section>

        <section className="settings-card">
          <h2>▽ Notification Preferences</h2>

          <div className="preference-row">
            <div>
              <strong>Push Notifications</strong>
              <p>Receive real-time alerts on your device for critical updates.</p>
            </div>

            <button
              className={pushNotifications ? "toggle active" : "toggle"}
              type="button"
              onClick={() => setPushNotifications(!pushNotifications)}
              aria-label="Toggle push notifications"
            />
          </div>

          <div className="preference-row">
            <div>
              <strong>Email Alerts</strong>
              <p>Weekly summaries and major platform news sent directly to your inbox.</p>
            </div>

            <button
              className={emailAlerts ? "toggle active" : "toggle"}
              type="button"
              onClick={() => setEmailAlerts(!emailAlerts)}
              aria-label="Toggle email alerts"
            />
          </div>

          <div className="preference-row">
            <div>
              <strong>
                High Busyness Alerts <span>Priority</span>
              </strong>
              <p>
                Get notified immediately when saved healthcare locations exceed
                85% capacity.
              </p>
            </div>

            <button
              className={busynessAlerts ? "toggle active" : "toggle"}
              type="button"
              onClick={() => setBusynessAlerts(!busynessAlerts)}
              aria-label="Toggle high busyness alerts"
            />
          </div>
        </section>

        <section className="settings-card">
          <h2>▣ Privacy & Security</h2>

          <div className="privacy-grid">
            <div className="location-box">
              <div className="privacy-top-row">
                <strong>Location Sharing</strong>

                <button
                  className={locationSharing ? "toggle active" : "toggle"}
                  type="button"
                  onClick={() => setLocationSharing(!locationSharing)}
                  aria-label="Toggle location sharing"
                />
              </div>

              <p>Allow ClearPath to use your GPS to provide local facility routing.</p>
              <a href="#">Data is anonymized before transmission.</a>
            </div>

            <div className="legal-box">
              <strong>Legal Documents</strong>

              <button type="button" onClick={() => navigate("/privacy-policy")}>
                Privacy Policy <span>↗</span>
              </button>

              <button type="button" onClick={() => navigate("/terms")}>
                Terms of Service <span>↗</span>
              </button>
            </div>
          </div>
        </section>

        <section className="settings-card">
          <h2>▤ Data Management</h2>

          <strong className="export-title">Export Data</strong>

          <div className="export-box">
            <div className="export-icon">⇩</div>

            <div>
              <strong>Export Personal Health Data</strong>
              <p>Download a GDPR-compliant JSON or CSV of your activity logs.</p>
            </div>

            <button type="button" onClick={handleExportData}>
              Initiate Export
            </button>
          </div>
        </section>

        <section className="settings-card danger-card">
          <div className="danger-label">⚠ DANGER ZONE</div>

          <div className="danger-panel">
            <h3>Delete Account</h3>

            <p>
              Once deleted, your profile, saved locations, and medical history
              metrics cannot be recovered. All local data cached on this device
              will be erased immediately.
            </p>

            <button type="button" onClick={handleDeleteAccount}>
              🗑 Delete Account & Erase All Local Data
            </button>
          </div>
        </section>

        <footer className="settings-footer">
          <p>ClearPath Preview App v0.1.0-alpha</p>
          <p>© 2026 DataHealth Intelligence. All Rights Reserved.</p>
        </footer>
      </section>
    </main>
  );
}

export default Settings;
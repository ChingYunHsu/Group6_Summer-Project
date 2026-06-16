import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { USER_PROFILE } from "../data/userProfile";

const ALL_LANGUAGES = [
  "Arabic", "Bengali", "Chinese", "Dutch", "English", "French", "German",
  "Greek", "Hindi", "Irish", "Italian", "Japanese", "Korean", "Polish",
  "Portuguese", "Romanian", "Russian", "Spanish", "Turkish", "Ukrainian",
  "Vietnamese"
];

const PROFICIENCY_LEVELS = ["Native", "Fluent", "Intermediate", "Basic"];

function Profile() {
  const navigate = useNavigate();

  const [languages, setLanguages] = useState(USER_PROFILE.spoken_languages);
  const [showLanguageModal, setShowLanguageModal] = useState(false);
  const [languageSearch, setLanguageSearch] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("");
  const [selectedLevel, setSelectedLevel] = useState("Fluent");

  const filteredLanguages = ALL_LANGUAGES.filter((language) =>
    language.toLowerCase().includes(languageSearch.toLowerCase())
  );

  function handleAddLanguage() {
    if (!selectedLanguage) return;

    const newLanguage = `${selectedLanguage} (${selectedLevel})`;

    if (!languages.includes(newLanguage)) {
      setLanguages([...languages, newLanguage]);
    }

    setShowLanguageModal(false);
    setLanguageSearch("");
    setSelectedLanguage("");
    setSelectedLevel("Fluent");
  }

  return (
    <main className="profile-single-column-page">
      <section className="privacy-notice">
        <div className="privacy-icon">🛡</div>
        <div>
          <h1>Clinical Data Privacy</h1>
          <p>
            Your medical critical information is stored exclusively on this
            mobile device for maximum security. ClearPath does not store health
            records on our servers. You can securely access and share your data
            for printing or medical review via an encrypted QR Sync at authorized
            terminals.
          </p>
        </div>
      </section>

      <section className="account-hero">
        <div className="account-identity">
          <div className="profile-photo-wrap">
            <div className="profile-photo profile-photo-fallback">AR</div>
            <button className="photo-edit-button" type="button">
              ✎
            </button>
          </div>

          <div>
            <h2>Personal Account</h2>
            <p>Healthcare Intelligence ID: CP-9921024-ER</p>
          </div>
        </div>

        <button
          className="outline-profile-button"
          type="button"
          onClick={() => navigate("/profile/edit")}
        >
          Edit Profile
        </button>
      </section>

      <section className="identity-panel">
        <div className="identity-field locked-field">
          <span>User ID</span>
          <strong>CP-9921024-ER <small>🔒</small></strong>
        </div>

        <div className="identity-field locked-field">
          <span>Full Name</span>
          <strong>{USER_PROFILE.full_name} <small>🔒</small></strong>
        </div>

        <div className="identity-field locked-field">
          <span>Email Address</span>
          <strong>{USER_PROFILE.email} <small>🔒</small></strong>
        </div>

        <div></div>

        <div className="identity-field editable-field">
          <span>Phone Number</span>
          <input value={USER_PROFILE.phone} readOnly />
        </div>

        <div className="identity-field editable-field">
          <span>Nationality</span>
          <input value={USER_PROFILE.nationality} readOnly />
        </div>

        <div className="identity-field identity-field-wide">
          <span>Spoken Languages</span>

          <div className="language-chip-row">
            {languages.map((language) => (
              <span
                className={
                  language.includes("Native")
                    ? "language-chip native"
                    : "language-chip"
                }
                key={language}
              >
                {language}
              </span>
            ))}

            <button
              className="add-language-chip"
              type="button"
              onClick={() => setShowLanguageModal(true)}
            >
              + Add Language
            </button>
          </div>
        </div>
      </section>

      <section className="qr-sync-section">
        <button
          className="qr-sync-button"
          type="button"
          onClick={() => navigate("/medical-card")}
        >
          <span>▦</span>
          Print Medical Passport via QR Sync ›
        </button>
        <p>Clinical records remain local until QR Sync is authorised.</p>
      </section>

      <footer className="profile-footer">
        <span>Privacy First</span>
        <span>Encrypted QR Sync</span>
        <span>Local Clinical Storage</span>
      </footer>

      {showLanguageModal && (
        <div className="language-modal-overlay">
          <div className="language-modal">
            <h2>Add Spoken Language</h2>

            <label>
              Search language
              <input
                type="text"
                value={languageSearch}
                onChange={(e) => setLanguageSearch(e.target.value)}
                placeholder="Type a language name..."
              />
            </label>

            <div className="language-dropdown">
              {filteredLanguages.length > 0 ? (
                filteredLanguages.map((language) => (
                  <button
                    key={language}
                    type="button"
                    className={
                      selectedLanguage === language ? "selected-language" : ""
                    }
                    onClick={() => setSelectedLanguage(language)}
                  >
                    {language}
                  </button>
                ))
              ) : (
                <p>No languages found</p>
              )}
            </div>

            <label>
              Proficiency
              <select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
              >
                {PROFICIENCY_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>

            <div className="language-modal-actions">
              <button
                type="button"
                onClick={() => setShowLanguageModal(false)}
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleAddLanguage}
                disabled={!selectedLanguage}
              >
                Add Language
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default Profile;
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMedicalProfile } from "../services/MedicalProfileApi";
import "./Profile.css";

function Profile() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadMedicalProfile() {
      try {
        setIsLoading(true);
        setError("");

        const serverProfile = await getMedicalProfile();
        setProfile(serverProfile);
      } catch (error) {
        console.error("Failed to load medical profile:", error);
        setError(
          error.message ||
            "Could not load medical profile. Backend may not be ready yet."
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadMedicalProfile();
  }, []);

  if (isLoading) {
    return (
      <main className="profile-page">
        <p>Loading medical profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="profile-page">
        <p className="profile-error">
          {error || "No medical profile available."}
        </p>
      </main>
    );
  }

  return (
    <main className="profile-page">
      <div className="profile-title-row">
        <div>
          <h1>Personal & Medical Profile</h1>
          <p>
            Securely manage your personal identification and critical medical
            information. This data is used for emergency wayfinding and clinical
            insights.
          </p>
        </div>

        <div className="profile-actions">
          <button onClick={() => navigate("/profile/edit")}>✎ Edit</button>
          <button onClick={() => navigate("/medical-card")}>
            ⎙ Print Medical Card
          </button>
        </div>
      </div>

      <section className="profile-grid">
        <aside className="profile-left">
          <div className="profile-card identity-card">
            <div className="avatar-box">👩🏻‍⚕️</div>
            <h2>{profile.full_name || profile.display_name || "Not provided"}</h2>
            <span className="verified-badge">⊙ Verified Patient</span>

            <div className="info-line">
              <span>DOB</span>
              <strong>{profile.date_of_birth || "Not provided"}</strong>
            </div>

            <div className="info-line">
              <span>Gender</span>
              <strong>{profile.gender || "Not provided"}</strong>
            </div>
          </div>

          <div className="profile-card">
            <h3>▧ Contact Information</h3>
            <p>
              <strong>Phone Number</strong>
              <br />
              {profile.phone || "Not provided"}
            </p>
            <p>
              <strong>Email Address</strong>
              <br />
              {profile.email || "Not provided"}
            </p>
            <p>
              <strong>Primary Address</strong>
              <br />
              {profile.address || "Not provided"}
            </p>
          </div>
        </aside>

        <section className="profile-right">
          <div className="top-cards">
            <div className="profile-card vital-card">
              <h3>Vital Signs</h3>
              <div className="blood-row">
                <span className="blood-type">{profile.blood_type || "N/A"}</span>
                <p>
                  <strong>Blood Type</strong>
                </p>
              </div>
            </div>

            <div className="profile-card language-card">
              <h3>Spoken Languages</h3>

              <div className="tag-list">
                {(profile.spoken_languages ?? []).map((language) => (
                  <span key={language}>{language}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="profile-card clinical-card">
            <h2>▣ Clinical Profile</h2>

            <div className="clinical-columns">
              <div>
                <h3 className="warning-heading">△ Allergies</h3>

                {(profile.allergies ?? []).length > 0 ? (
                  profile.allergies.map((allergy) => (
                    <div
                      className="medical-item red-dot"
                      key={allergy.name || allergy}
                    >
                      <strong>{allergy.name || allergy}</strong>
                      <p>{allergy.detail || ""}</p>
                    </div>
                  ))
                ) : (
                  <p>No known allergies listed.</p>
                )}
              </div>

              <div>
                <h3 className="condition-heading">⌘ Medical Conditions</h3>

                {(profile.medical_conditions ?? []).length > 0 ? (
                  profile.medical_conditions.map((condition) => (
                    <div
                      className="medical-item blue-dot"
                      key={condition.name || condition}
                    >
                      <strong>{condition.name || condition}</strong>
                      <p>{condition.detail || ""}</p>
                    </div>
                  ))
                ) : (
                  <p>No medical conditions listed.</p>
                )}
              </div>
            </div>
          </div>

          <div className="profile-card">
            <h2>✱ Emergency Contacts</h2>

            <div className="contacts-grid">
              {(profile.emergency_contacts ?? []).length > 0 ? (
                profile.emergency_contacts.map((contact) => (
                  <div className="contact-box" key={contact.name}>
                    <div className="contact-top">
                      <strong>{contact.name}</strong>
                      {contact.primary && <span>Primary</span>}
                    </div>
                    <p>{contact.relationship}</p>
                    <p>{contact.phone}</p>
                  </div>
                ))
              ) : (
                <p>No emergency contacts listed.</p>
              )}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

export default Profile;
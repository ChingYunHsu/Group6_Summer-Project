import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMedicalProfile } from "../services/MedicalProfileApi";
import { getUserProfile } from "../services/UserProfileApi";
import "./Profile.css";

function Profile() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProfile() {
      try {
        setIsLoading(true);
        setError("");

        const [userProfile, medicalProfile] = await Promise.all([
          getUserProfile(),
          getMedicalProfile(),
        ]);

        console.log("USER PROFILE RESPONSE:", userProfile);
        console.log("MEDICAL PROFILE RESPONSE:", medicalProfile);

        const combinedProfile = {
          ...medicalProfile,
          ...userProfile,

          // Keep medical fields from medical profile
          date_of_birth:
            medicalProfile.date_of_birth || userProfile.date_of_birth || "",
          gender: medicalProfile.gender || userProfile.gender || "",
          address: medicalProfile.address || userProfile.address || "",
          blood_type: medicalProfile.blood_type || "",

          // Normalise backend naming
          allergies: Array.isArray(medicalProfile.allergies)
            ? medicalProfile.allergies
            : [],

          medical_conditions: Array.isArray(medicalProfile.medical_conditions)
            ? medicalProfile.medical_conditions
            : Array.isArray(medicalProfile.conditions)
              ? medicalProfile.conditions
              : [],

          emergency_contacts: Array.isArray(medicalProfile.emergency_contacts)
            ? medicalProfile.emergency_contacts
            : [],

          spoken_languages: Array.isArray(userProfile.spoken_languages)
            ? userProfile.spoken_languages
            : [],
        };

        setProfile(combinedProfile);
      } catch (error) {
        console.error("Failed to load profile:", error);
        setError(
          error.message ||
            "Could not load profile. Backend may not be ready yet."
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadProfile();
  }, []);

  if (isLoading) {
    return (
      <main className="profile-page">
        <p>Loading profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="profile-page">
        <p className="profile-error">{error || "No profile available."}</p>
      </main>
    );
  }

  const allergies = Array.isArray(profile.allergies)
    ? profile.allergies
    : [];

  const medicalConditions = Array.isArray(profile.medical_conditions)
    ? profile.medical_conditions
    : [];

  const emergencyContacts = Array.isArray(profile.emergency_contacts)
    ? profile.emergency_contacts
    : [];

  const spokenLanguages = Array.isArray(profile.spoken_languages)
    ? profile.spoken_languages
    : [];

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
          <button type="button" onClick={() => navigate("/profile/edit")}>
            ✎ Edit
          </button>

          <button type="button" onClick={() => navigate("/medical-card")}>
            ⎙ Print Medical Card
          </button>
        </div>
      </div>

      <section className="profile-grid">
        <aside className="profile-left">
          <div className="profile-card identity-card">
            <div className="avatar-box">👩🏻‍⚕️</div>

            <h2>
              {profile.full_name ||
                profile.display_name ||
                profile.email ||
                "Not provided"}
            </h2>

            <span className="verified-badge">⊙ Verified Patient</span>

            <div className="info-line">
              <span>DOB</span>
              <strong>{profile.date_of_birth || "Not provided"}</strong>
            </div>

            <div className="info-line">
              <span>Gender</span>
              <strong>{profile.gender || "Not provided"}</strong>
            </div>

            <div className="info-line">
              <span>Nationality</span>
              <strong>{profile.nationality || "Not provided"}</strong>
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
                <span className="blood-type">
                  {profile.blood_type || "N/A"}
                </span>

                <p>
                  <strong>Blood Type</strong>
                </p>
              </div>
            </div>

            <div className="profile-card language-card">
              <h3>Spoken Languages</h3>

              <div className="tag-list">
                {spokenLanguages.length > 0 ? (
                  spokenLanguages.map((language) => (
                    <span key={language}>{language}</span>
                  ))
                ) : (
                  <p>Not provided</p>
                )}
              </div>
            </div>
          </div>

          <div className="profile-card clinical-card">
            <h2>▣ Clinical Profile</h2>

            <div className="clinical-columns">
              <div>
                <h3 className="warning-heading">△ Allergies</h3>

                {allergies.length > 0 ? (
                  allergies.map((allergy, index) => (
                    <div
                      className="medical-item red-dot"
                      key={allergy.name || allergy || index}
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

                {medicalConditions.length > 0 ? (
                  medicalConditions.map((condition, index) => (
                    <div
                      className="medical-item blue-dot"
                      key={condition.name || condition || index}
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
              {emergencyContacts.length > 0 ? (
                emergencyContacts.map((contact, index) => (
                  <div
                    className="contact-box"
                    key={contact.name || contact.phone || index}
                  >
                    <div className="contact-top">
                      <strong>{contact.name || "Not provided"}</strong>
                      {contact.primary && <span>Primary</span>}
                    </div>

                    <p>{contact.relationship || "Not provided"}</p>
                    <p>{contact.phone || "Not provided"}</p>
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
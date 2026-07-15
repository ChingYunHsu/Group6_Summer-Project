import {
  useCallback,
  useEffect,
  useState,
} from "react";
import "./MedicalCard.css";

import {
  getMedicalProfile,
} from "../services/MedicalProfileApi";
import {
  getUserProfile,
} from "../services/UserProfileApi";

function normaliseProfile(
  userProfile = {},
  medicalProfile = {}
) {
  const allergies = Array.isArray(
    medicalProfile.allergies
  )
    ? medicalProfile.allergies
    : [];

  const medicalConditions = Array.isArray(
    medicalProfile.medical_conditions
  )
    ? medicalProfile.medical_conditions
    : Array.isArray(medicalProfile.conditions)
      ? medicalProfile.conditions
      : [];

  const emergencyContacts = Array.isArray(
    medicalProfile.emergency_contacts
  )
    ? medicalProfile.emergency_contacts
    : [];

  const spokenLanguages = Array.isArray(
    userProfile.spoken_languages
  )
    ? userProfile.spoken_languages
    : [];

  return {
    ...medicalProfile,
    ...userProfile,

    full_name:
      userProfile.full_name ||
      userProfile.display_name ||
      medicalProfile.full_name ||
      "",

    display_name:
      userProfile.display_name ||
      userProfile.full_name ||
      medicalProfile.display_name ||
      "",

    email: userProfile.email || "",
    phone: userProfile.phone || "",
    nationality: userProfile.nationality || "",
    spoken_languages: spokenLanguages,

    date_of_birth:
      medicalProfile.date_of_birth || "",
    gender: medicalProfile.gender || "",
    blood_type: medicalProfile.blood_type || "",
    address: medicalProfile.address || "",

    allergies,
    medical_conditions: medicalConditions,
    conditions: medicalConditions,
    emergency_contacts: emergencyContacts,

    medications: Array.isArray(
      medicalProfile.medications
    )
      ? medicalProfile.medications
      : [],
  };
}

function MedicalCard() {
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [
    isPreparingPrint,
    setIsPreparingPrint,
  ] = useState(false);
  const [error, setError] = useState("");

  const loadProfile = useCallback(async () => {
    const [userProfile, medicalProfile] =
      await Promise.all([
        getUserProfile(),
        getMedicalProfile(),
      ]);

    console.log(
      "MEDICAL CARD USER PROFILE:",
      userProfile
    );
    console.log(
      "MEDICAL CARD MEDICAL PROFILE:",
      medicalProfile
    );

    const combinedProfile = normaliseProfile(
      userProfile,
      medicalProfile
    );

    setProfile(combinedProfile);

    return combinedProfile;
  }, []);

  useEffect(() => {
    const initialLoadTimeout = window.setTimeout(
      () => {
        async function initialisePage() {
          try {
            setError("");
            await loadProfile();
          } catch (loadError) {
            console.error(
              "Failed to load medical card profile:",
              loadError
            );

            setError(
              loadError.message ||
                "Could not load medical profile."
            );
          } finally {
            setIsLoading(false);
          }
        }

        void initialisePage();
      },
      0
    );

    return () => {
      window.clearTimeout(initialLoadTimeout);
    };
  }, [loadProfile]);

  async function handlePrint() {
    try {
      setIsPreparingPrint(true);
      setError("");

      const latestProfile = await loadProfile();

      if (!latestProfile) {
        throw new Error(
          "No medical profile returned from backend."
        );
      }

      window.setTimeout(() => {
        window.print();
        setIsPreparingPrint(false);
      }, 150);
    } catch (printError) {
      console.error(
        "Failed to prepare medical passport:",
        printError
      );

      setError(
        printError.message ||
          "Could not prepare Medical Passport."
      );

      setIsPreparingPrint(false);
    }
  }

  if (isLoading) {
    return (
      <main className="medical-card-page">
        <p>Loading medical profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="medical-card-page">
        <p className="medical-error">
          {error ||
            "No medical profile available."}
        </p>
      </main>
    );
  }

  const allergies = Array.isArray(
    profile.allergies
  )
    ? profile.allergies
    : [];

  const medicalConditions = Array.isArray(
    profile.medical_conditions
  )
    ? profile.medical_conditions
    : [];

  const emergencyContacts = Array.isArray(
    profile.emergency_contacts
  )
    ? profile.emergency_contacts
    : [];

  const primaryContact =
    emergencyContacts.find(
      (contact) => contact.primary
    ) ||
    emergencyContacts[0] ||
    null;

  return (
    <main className="medical-card-page">
      <section className="medical-preview-header print-hide">
        <h1>Medical Document Preview</h1>

        <p>
          Review your critical health information before
          generating a printable A4 emergency document.
        </p>
      </section>

      {error && (
        <p className="medical-error print-hide">
          {error}
        </p>
      )}

      <section className="medical-a4-canvas">
        <header className="medical-alert-header">
          <div>
            <h2>MEDICAL ALERT</h2>
            <span>ALERTA MÉDICA</span>
          </div>

          <div className="medical-cross-icon">
            ✚
          </div>
        </header>

        <section className="medical-card-body">
          <div className="medical-top-grid">
            <div>
              <span className="medical-label">
                NAME / NOMBRE
              </span>

              <h3>
                {profile.full_name ||
                  profile.display_name ||
                  "Not provided"}
              </h3>
            </div>

            <div className="blood-preview">
              <span className="medical-label">
                BLOOD / SANGRE
              </span>

              <strong>
                {profile.blood_type || "N/A"}
              </strong>

              <small>
                {profile.donor_status || ""}
              </small>
            </div>
          </div>

          <div className="medical-section-grid">
            <div>
              <h4>ALLERGIES / ALERGIAS</h4>

              {allergies.length > 0 ? (
                allergies.map(
                  (allergy, index) => (
                    <div
                      className="medical-alert-item red-item"
                      key={
                        allergy.name ||
                        allergy ||
                        index
                      }
                    >
                      <div className="medical-alert-item-content">
                        <strong>
                          {allergy.name || allergy}
                        </strong>

                        <p>
                          {allergy.detail || ""}
                        </p>
                      </div>
                    </div>
                  )
                )
              ) : (
                <p>No known allergies listed.</p>
              )}
            </div>

            <div>
              <h4>
                MEDICAL CONDITIONS / CONDICIONES
                MÉDICAS
              </h4>

              {medicalConditions.length > 0 ? (
                medicalConditions.map(
                  (condition, index) => (
                    <div
                      className="medical-alert-item blue-item"
                      key={
                        condition.name ||
                        condition ||
                        index
                      }
                    >
                      <div className="medical-alert-item-content">
                        <strong>
                          {condition.name ||
                            condition}
                        </strong>

                        <p>
                          {condition.detail || ""}
                        </p>
                      </div>
                    </div>
                  )
                )
              ) : (
                <p>
                  No medical conditions listed.
                </p>
              )}
            </div>
          </div>

          <div className="medical-bottom-grid">
            <div>
              <h4>
                PERSONAL INFO / INFORMACIÓN PERSONAL
              </h4>

              <p>
                <strong>DOB / Nac:</strong>{" "}
                {profile.date_of_birth ||
                  "Not provided"}
              </p>

              <p>
                <strong>Nat:</strong>{" "}
                {profile.nationality ||
                  "Not provided"}
              </p>

              <p>
                <strong>Gen:</strong>{" "}
                {profile.gender || "Not provided"}
              </p>

              <h4>PHONE / TELÉFONO</h4>

              <p>
                {profile.phone || "Not provided"}
              </p>
            </div>

            <div>
              <h4>ADDRESS / DIRECCIÓN</h4>

              <p>
                {profile.address || "Not provided"}
              </p>

              {primaryContact ? (
                <div className="emergency-contact-card">
                  <h4>
                    EMERGENCY / EMERGENCIA
                  </h4>

                  <strong>
                    {primaryContact.name ||
                      "Not provided"}
                  </strong>

                  <p>
                    {primaryContact.relationship ||
                      "Not provided"}
                  </p>

                  {primaryContact.phone ? (
                    <a
                      href={`tel:${primaryContact.phone}`}
                    >
                      {primaryContact.phone}
                    </a>
                  ) : (
                    <p>Phone not provided</p>
                  )}
                </div>
              ) : (
                <div className="emergency-contact-card">
                  <h4>
                    EMERGENCY / EMERGENCIA
                  </h4>

                  <p>
                    No emergency contact listed.
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </section>

      <button
        className="print-medical-button print-hide"
        type="button"
        onClick={handlePrint}
        disabled={isPreparingPrint}
      >
        {isPreparingPrint
          ? "Preparing Medical Pass..."
          : "⎙ Print My Medical Pass (PDF)"}
      </button>

      <p className="a4-note print-hide">
        ⓘ Designed for standard A4 document size:
        210mm × 297mm
      </p>
    </main>
  );
}

export default MedicalCard;
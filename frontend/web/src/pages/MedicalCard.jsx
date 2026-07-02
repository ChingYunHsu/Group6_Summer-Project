import { useEffect, useState } from "react";
import "./MedicalCard.css";
import { getMedicalProfile } from "../services/ProfileApi";

function MedicalCard() {
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPreparingPrint, setIsPreparingPrint] = useState(false);
  const [error, setError] = useState("");

  async function loadProfile() {
    const serverProfile = await getMedicalProfile();
    setProfile(serverProfile);
    return serverProfile;
  }

  useEffect(() => {
    async function initialisePage() {
      try {
        setIsLoading(true);
        setError("");
        await loadProfile();
      } catch (error) {
        console.error("Failed to load medical profile:", error);
        setError(error.message || "Could not load medical profile.");
      } finally {
        setIsLoading(false);
      }
    }

    initialisePage();
  }, []);

  async function handlePrint() {
    try {
      setIsPreparingPrint(true);
      setError("");

      const latestProfile = await loadProfile();

      if (!latestProfile) {
        throw new Error("No medical profile returned from backend.");
      }

      setTimeout(() => {
        window.print();
        setIsPreparingPrint(false);
      }, 150);
    } catch (error) {
      console.error("Failed to prepare medical passport:", error);
      setError(error.message || "Could not prepare Medical Passport.");
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
          {error || "No medical profile available."}
        </p>
      </main>
    );
  }

  const primaryContact =
    (profile.emergency_contacts ?? []).find((contact) => contact.primary) ||
    (profile.emergency_contacts ?? [])[0] ||
    null;

  return (
    <main className="medical-card-page">
      <section className="medical-preview-header print-hide">
        <h1>Medical Document Preview</h1>
        <p>
          Review your critical health information before generating a printable
          A4 emergency document.
        </p>
      </section>

      {error && <p className="medical-error print-hide">{error}</p>}

      <section className="medical-a4-canvas">
        <header className="medical-alert-header">
          <div>
            <h2>MEDICAL ALERT</h2>
            <span>ALERTA MÉDICA</span>
          </div>
          <div className="medical-cross-icon">✚</div>
        </header>

        <section className="medical-card-body">
          <div className="medical-top-grid">
            <div>
              <span className="medical-label">NAME / NOMBRE</span>
              <h3>{profile.full_name || profile.display_name || "Not provided"}</h3>
            </div>

            <div className="blood-preview">
              <span className="medical-label">BLOOD / SANGRE</span>
              <strong>{profile.blood_type || "N/A"}</strong>
              <small>{profile.donor_status || ""}</small>
            </div>
          </div>

          <div className="medical-section-grid">
            <div>
              <h4>ALLERGIES / ALERGIAS</h4>

              {(profile.allergies ?? []).length > 0 ? (
                profile.allergies.map((allergy) => (
                  <div
                    className="medical-alert-item red-item"
                    key={allergy.name || allergy}
                  >
                    <div className="medical-alert-item-content">
                      <strong>{allergy.name || allergy}</strong>
                      <p>{allergy.detail || ""}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p>No known allergies listed.</p>
              )}
            </div>

            <div>
              <h4>MEDICAL CONDITIONS / CONDICIONES MÉDICAS</h4>

              {(profile.medical_conditions ?? []).length > 0 ? (
                profile.medical_conditions.map((condition) => (
                  <div
                    className="medical-alert-item blue-item"
                    key={condition.name || condition}
                  >
                    <div className="medical-alert-item-content">
                      <strong>{condition.name || condition}</strong>
                      <p>{condition.detail || ""}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p>No medical conditions listed.</p>
              )}
            </div>
          </div>

          <div className="medical-bottom-grid">
            <div>
              <h4>PERSONAL INFO / INFORMACIÓN PERSONAL</h4>
              <p>
                <strong>DOB / Nac:</strong>{" "}
                {profile.date_of_birth || "Not provided"}
              </p>
              <p>
                <strong>Nat:</strong> {profile.nationality || "Not provided"}
              </p>
              <p>
                <strong>Gen:</strong> {profile.gender || "Not provided"}
              </p>

              <h4>PHONE / TELÉFONO</h4>
              <p>{profile.phone || "Not provided"}</p>
            </div>

            <div>
              <h4>ADDRESS / DIRECCIÓN</h4>
              <p>{profile.address || "Not provided"}</p>

              {primaryContact && (
                <div className="emergency-contact-card">
                  <h4>EMERGENCY / EMERGENCIA</h4>
                  <strong>{primaryContact.name}</strong>
                  <p>{primaryContact.relationship}</p>
                  <a href={`tel:${primaryContact.phone}`}>
                    {primaryContact.phone}
                  </a>
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
        ⓘ Designed for standard A4 document size: 210mm × 297mm
      </p>
    </main>
  );
}

export default MedicalCard;
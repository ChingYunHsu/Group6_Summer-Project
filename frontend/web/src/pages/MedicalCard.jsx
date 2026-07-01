import { USER_PROFILE } from "../data/userProfile";
import "./MedicalCard.css";
import { useLocation } from "react-router-dom";

function MedicalCard() {
  const primaryContact =
    USER_PROFILE.emergency_contacts.find((contact) => contact.primary) ||
    USER_PROFILE.emergency_contacts[0];
    const location = useLocation();
    const profile = location.state?.clinicalPayload || USER_PROFILE;
  
  function handlePrint() {
    window.print();
  }

  return (
    <main className="medical-card-page">
      <section className="medical-preview-header">
        <h1>Medical Document Preview</h1>
        <p>
          Review your critical health information before generating a printable
          A4 emergency document.
        </p>
      </section>

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
              <h3>{profile.full_name}</h3>
            </div>

            <div className="blood-preview">
              <span className="medical-label">BLOOD / SANGRE</span>
              <strong>{profile.blood_type}</strong>
              <small>{profile.donor_status}</small>
            </div>
          </div>

          <div className="medical-section-grid">
            <div>
              <h4>ALLERGIES / ALERGIAS</h4>
              {profile.allergies.map((allergy) => (
                <div className="medical-alert-item red-item" key={allergy.name}>
                  <div className="medical-alert-item-content">
                  <strong>{allergy.name}</strong>
                  <p>{allergy.detail}</p>
                </div>
                </div>
              ))}
            </div>

            <div>
              <h4>MEDICAL CONDITIONS / CONDICIONES MÉDICAS</h4>
              {profile.medical_conditions.map((condition) => (
                <div className="medical-alert-item blue-item" key={condition.name}>
                  <div className="medical-alert-item-content">
                  <strong>{condition.name}</strong>
                  <p>{condition.detail}</p>
                </div>
                </div>
              ))}
            </div>
          </div>

          <div className="medical-bottom-grid">
            <div>
              <h4>PERSONAL INFO / INFORMACIÓN PERSONAL</h4>
              <p>
                <strong>DOB / Nac:</strong> {profile.date_of_birth}
              </p>
              <p>
                <strong>Nat:</strong> {profile.nationality}
              </p>
              <p>
                <strong>Gen:</strong> {profile.gender}
              </p>

              <h4>PHONE / TELÉFONO</h4>
              <p>{profile.phone}</p>
            </div>

            <div>
              <h4>ADDRESS / DIRECCIÓN</h4>
              <p>{profile.address}</p>

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

      <button className="print-medical-button" type="button" onClick={handlePrint}>
        ⎙ Print My Medical Pass (PDF)
      </button>

      <p className="a4-note">
        ⓘ Designed for standard A4 document size: 210mm × 297mm
      </p>
    </main>
  );
}

export default MedicalCard;
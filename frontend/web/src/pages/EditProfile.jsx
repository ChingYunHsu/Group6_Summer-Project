import { useEffect, useState } from "react";
import "./EditProfile.css";
import { useNavigate } from "react-router-dom";

import {
  getMedicalProfile,
  updateMedicalProfile,
} from "../services/MedicalProfileApi";

import {
  getUserProfile,
  updateUserProfile,
} from "../services/UserProfileApi";

function EditProfile() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    date_of_birth: "",
    gender: "",
    blood_type: "",
    phone: "",
    email: "",
    nationality: "",
    spoken_languages_text: "",
    address: "",
  });

  const [allergies, setAllergies] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [contacts, setContacts] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const [showConditionModal, setShowConditionModal] = useState(false);
  const [conditionName, setConditionName] = useState("");
  const [conditionDetail, setConditionDetail] = useState("");
  const [editingConditionIndex, setEditingConditionIndex] = useState(null);

  const [showAllergyModal, setShowAllergyModal] = useState(false);
  const [allergyName, setAllergyName] = useState("");
  const [allergyDetail, setAllergyDetail] = useState("");
  const [editingAllergyIndex, setEditingAllergyIndex] = useState(null);

  const [showContactModal, setShowContactModal] = useState(false);
  const [contactName, setContactName] = useState("");
  const [contactRelationship, setContactRelationship] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [editingContactIndex, setEditingContactIndex] = useState(null);

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

        const spokenLanguages = Array.isArray(userProfile.spoken_languages)
          ? userProfile.spoken_languages
          : [];

        setForm({
          full_name:
            userProfile.full_name ||
            userProfile.display_name ||
            medicalProfile.full_name ||
            "",
          date_of_birth: medicalProfile.date_of_birth || "",
          gender: medicalProfile.gender || "",
          blood_type: medicalProfile.blood_type || "",
          phone: userProfile.phone || "",
          email: userProfile.email || "",
          nationality: userProfile.nationality || "",
          spoken_languages_text: spokenLanguages.join(", "),
          address: medicalProfile.address || "",
        });

        setAllergies(
          Array.isArray(medicalProfile.allergies)
            ? medicalProfile.allergies
            : []
        );

        setConditions(
          Array.isArray(medicalProfile.medical_conditions)
            ? medicalProfile.medical_conditions
            : Array.isArray(medicalProfile.conditions)
              ? medicalProfile.conditions
              : []
        );

        setContacts(
          Array.isArray(medicalProfile.emergency_contacts)
            ? medicalProfile.emergency_contacts
            : []
        );
      } catch (error) {
        console.error("Failed to load profile for editing:", error);
        setError(error.message || "Could not load profile.");
      } finally {
        setIsLoading(false);
      }
    }

    loadProfile();
  }, []);

  function updateFormField(fieldName, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [fieldName]: value,
    }));
  }

  function getSpokenLanguagesArray() {
    return form.spoken_languages_text
      .split(",")
      .map((language) => language.trim())
      .filter(Boolean);
  }

  function openConditionModal() {
    setConditionName("");
    setConditionDetail("");
    setEditingConditionIndex(null);
    setShowConditionModal(true);
  }

  function editCondition(index) {
    setConditionName(conditions[index].name || "");
    setConditionDetail(conditions[index].detail || "");
    setEditingConditionIndex(index);
    setShowConditionModal(true);
  }

  function closeConditionModal() {
    setShowConditionModal(false);
    setEditingConditionIndex(null);
  }

  function saveCondition() {
    if (!conditionName.trim()) return;

    const conditionData = {
      name: conditionName.trim(),
      detail: conditionDetail.trim() || "No details provided",
    };

    if (editingConditionIndex !== null) {
      const updated = [...conditions];
      updated[editingConditionIndex] = conditionData;
      setConditions(updated);
    } else {
      setConditions([...conditions, conditionData]);
    }

    closeConditionModal();
  }

  function deleteCondition(index) {
    setConditions(conditions.filter((_, itemIndex) => itemIndex !== index));
  }

  function openAllergyModal() {
    setAllergyName("");
    setAllergyDetail("");
    setEditingAllergyIndex(null);
    setShowAllergyModal(true);
  }

  function editAllergy(index) {
    setAllergyName(allergies[index].name || "");
    setAllergyDetail(allergies[index].detail || "");
    setEditingAllergyIndex(index);
    setShowAllergyModal(true);
  }

  function closeAllergyModal() {
    setShowAllergyModal(false);
    setEditingAllergyIndex(null);
  }

  function saveAllergy() {
    if (!allergyName.trim()) return;

    const allergyData = {
      name: allergyName.trim(),
      detail: allergyDetail.trim() || "No details provided",
    };

    if (editingAllergyIndex !== null) {
      const updated = [...allergies];
      updated[editingAllergyIndex] = allergyData;
      setAllergies(updated);
    } else {
      setAllergies([...allergies, allergyData]);
    }

    closeAllergyModal();
  }

  function deleteAllergy(index) {
    setAllergies(allergies.filter((_, itemIndex) => itemIndex !== index));
  }

  function openContactModal() {
    setContactName("");
    setContactRelationship("");
    setContactPhone("");
    setEditingContactIndex(null);
    setShowContactModal(true);
  }

  function editContact(index) {
    setContactName(contacts[index].name || "");
    setContactRelationship(contacts[index].relationship || "");
    setContactPhone(contacts[index].phone || "");
    setEditingContactIndex(index);
    setShowContactModal(true);
  }

  function closeContactModal() {
    setShowContactModal(false);
    setEditingContactIndex(null);
  }

  function saveContact() {
    if (!contactName.trim()) return;

    const contactData = {
      name: contactName.trim(),
      relationship: contactRelationship.trim() || "Emergency Contact",
      phone: contactPhone.trim() || "No phone provided",
    };

    if (editingContactIndex !== null) {
      const updated = [...contacts];
      updated[editingContactIndex] = contactData;
      setContacts(updated);
    } else {
      setContacts([...contacts, contactData]);
    }

    closeContactModal();
  }

  function deleteContact(index) {
    setContacts(contacts.filter((_, itemIndex) => itemIndex !== index));
  }

  async function handleSaveProfile() {
    try {
      setIsSaving(true);
      setError("");

      const userProfilePayload = {
        phone: form.phone || "",
        nationality: form.nationality || "",
        spoken_languages: form.spoken_languages_text
          .split(",")
          .map((language) => language.trim())
          .filter(Boolean),
        };

      const medicalProfilePayload = {
        date_of_birth: form.date_of_birth || null,
        gender: form.gender || null,
        blood_type: form.blood_type || null,
        address: form.address || null,
        allergies,
        conditions,
        medications: [],
        emergency_contacts: contacts,
      };

      console.log("Saving user profile:", userProfilePayload);
      console.log("Saving medical profile:", medicalProfilePayload);

      await Promise.all([
        updateUserProfile(userProfilePayload),
        updateMedicalProfile(medicalProfilePayload),
      ]);

      navigate("/profile");
    } catch (error) {
      console.error("Failed to save profile:", error);

      const problemFields = [
        ...(error?.body?.missing_fields ?? []),
        ...(error?.body?.invalid_fields ?? []),
      ];

      const message = problemFields.length
        ? `${error.message} (${problemFields.join(", ")})`
        : error.message || "Could not save profile.";

      setError(message);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <main className="edit-profile-page">
        <p>Loading profile...</p>
      </main>
    );
  }

  return (
    <main className="edit-profile-page">
      <h1>Edit Personal & Medical Profile</h1>

      <p className="edit-subtitle">
        Update your core identity, vital signs, and clinical history for accurate
        care routing.
      </p>

      {error && <p className="profile-error">{error}</p>}

      <section className="edit-section">
        <h2>▣ Core Identity</h2>

        <div className="core-grid">
          <div className="edit-avatar"></div>

          <label>
            Full Name
            <input value={form.full_name} readOnly />
          </label>

          <label>
            Date of Birth
            <input
              type="date"
              value={form.date_of_birth}
              onChange={(event) =>
                updateFormField("date_of_birth", event.target.value)
              }
            />
          </label>

          <label>
            Gender
            <select
              value={form.gender}
              onChange={(event) =>
                updateFormField("gender", event.target.value)
              }
            >
              <option value="">Select gender</option>
              <option value="Female">Female</option>
              <option value="Male">Male</option>
              <option value="Other">Other</option>
            </select>
          </label>

          <label>
            Nationality
            <input
              value={form.nationality}
              onChange={(event) =>
                updateFormField("nationality", event.target.value)
              }
              placeholder="e.g. Irish"
            />
          </label>
        </div>
      </section>

      <section className="edit-section">
        <h2>♡ Vital Signs</h2>

        <label>
          Blood Type
          <select
            value={form.blood_type}
            onChange={(event) =>
              updateFormField("blood_type", event.target.value)
            }
          >
            <option value="">Select blood type</option>
            <option value="O+">O Positive (O+)</option>
            <option value="O-">O Negative (O-)</option>
            <option value="A+">A Positive (A+)</option>
            <option value="A-">A Negative (A-)</option>
            <option value="B+">B Positive (B+)</option>
            <option value="B-">B Negative (B-)</option>
            <option value="AB+">AB Positive (AB+)</option>
            <option value="AB-">AB Negative (AB-)</option>
          </select>
        </label>
      </section>

      <section className="edit-section">
        <h2>▣ Clinical Profile</h2>

        <div className="two-column-edit">
          <div>
            <div className="section-line-title">
              <h3>Allergies</h3>

              <button type="button" onClick={openAllergyModal}>
                + Add Allergy
              </button>
            </div>

            {allergies.length > 0 ? (
              allergies.map((allergy, index) => (
                <div className="editable-item" key={`${allergy.name}-${index}`}>
                  <div>
                    <strong>{allergy.name}</strong>
                    <p>{allergy.detail}</p>
                  </div>

                  <div className="item-actions">
                    <button type="button" onClick={() => editAllergy(index)}>
                      ✏️
                    </button>

                    <button type="button" onClick={() => deleteAllergy(index)}>
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p>No allergies added.</p>
            )}
          </div>

          <div>
            <div className="section-line-title">
              <h3>Medical Conditions</h3>

              <button type="button" onClick={openConditionModal}>
                + Add Condition
              </button>
            </div>

            {conditions.length > 0 ? (
              conditions.map((condition, index) => (
                <div
                  className="editable-item"
                  key={`${condition.name}-${index}`}
                >
                  <div>
                    <strong>{condition.name}</strong>
                    <p>{condition.detail}</p>
                  </div>

                  <div className="item-actions">
                    <button type="button" onClick={() => editCondition(index)}>
                      ✏️
                    </button>

                    <button
                      type="button"
                      onClick={() => deleteCondition(index)}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p>No medical conditions added.</p>
            )}
          </div>
        </div>
      </section>

      <section className="edit-section">
        <h2>▣ Contact Information</h2>

        <div className="contact-form-grid">
          <label>
            Phone Number
            <input
              value={form.phone}
              onChange={(event) =>
                updateFormField("phone", event.target.value)
              }
            />
          </label>

          <label>
            Email Address
            <input type="email" value={form.email} readOnly />
          </label>
        </div>

        <label>
          Spoken Languages
          <input
            value={form.spoken_languages_text}
            onChange={(event) =>
              updateFormField("spoken_languages_text", event.target.value)
            }
            placeholder="e.g. English, Chinese, Spanish"
          />
        </label>

        <label>
          Primary Address
          <textarea
            value={form.address}
            onChange={(event) =>
              updateFormField("address", event.target.value)
            }
          />
        </label>

        <div className="section-line-title emergency-title-row">
          <h3>Emergency Contacts</h3>

          <button type="button" onClick={openContactModal}>
            + Add Contact
          </button>
        </div>

        <div className="contact-row-list">
          {contacts.length > 0 ? (
            contacts.map((contact, index) => (
              <div className="editable-item" key={`${contact.name}-${index}`}>
                <div>
                  <strong>{contact.name}</strong>
                  <p>{contact.relationship}</p>
                  <p>{contact.phone}</p>
                </div>

                <div className="item-actions">
                  <button type="button" onClick={() => editContact(index)}>
                    ✏️
                  </button>

                  <button type="button" onClick={() => deleteContact(index)}>
                    🗑️
                  </button>
                </div>
              </div>
            ))
          ) : (
            <p>No emergency contacts added.</p>
          )}
        </div>

        <div className="edit-footer">
          <button type="button" onClick={() => navigate("/profile")}>
            Discard Changes
          </button>

          <button
            type="button"
            onClick={handleSaveProfile}
            disabled={isSaving}
          >
            {isSaving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </section>

      {showConditionModal && (
        <div className="edit-modal-overlay">
          <div className="edit-modal">
            <h2>
              {editingConditionIndex !== null
                ? "Edit Medical Condition"
                : "Add Medical Condition"}
            </h2>

            <label>
              Illness / Condition
              <input
                value={conditionName}
                onChange={(event) => setConditionName(event.target.value)}
                placeholder="e.g. Asthma"
              />
            </label>

            <label>
              Description
              <textarea
                value={conditionDetail}
                onChange={(event) => setConditionDetail(event.target.value)}
                placeholder="Describe diagnosis, medication, severity, or notes"
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeConditionModal}>
                Cancel
              </button>

              <button type="button" onClick={saveCondition}>
                Save Condition
              </button>
            </div>
          </div>
        </div>
      )}

      {showAllergyModal && (
        <div className="edit-modal-overlay">
          <div className="edit-modal">
            <h2>
              {editingAllergyIndex !== null ? "Edit Allergy" : "Add Allergy"}
            </h2>

            <label>
              Allergy
              <input
                value={allergyName}
                onChange={(event) => setAllergyName(event.target.value)}
                placeholder="e.g. Penicillin"
              />
            </label>

            <label>
              Reaction / Severity
              <textarea
                value={allergyDetail}
                onChange={(event) => setAllergyDetail(event.target.value)}
                placeholder="Describe reaction, severity, or clinical notes"
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeAllergyModal}>
                Cancel
              </button>

              <button type="button" onClick={saveAllergy}>
                Save Allergy
              </button>
            </div>
          </div>
        </div>
      )}

      {showContactModal && (
        <div className="edit-modal-overlay">
          <div className="edit-modal">
            <h2>
              {editingContactIndex !== null
                ? "Edit Emergency Contact"
                : "Add Emergency Contact"}
            </h2>

            <label>
              Contact Name
              <input
                value={contactName}
                onChange={(event) => setContactName(event.target.value)}
                placeholder="e.g. Marcus Rivera"
              />
            </label>

            <label>
              Relationship
              <input
                value={contactRelationship}
                onChange={(event) =>
                  setContactRelationship(event.target.value)
                }
                placeholder="e.g. Spouse"
              />
            </label>

            <label>
              Phone Number
              <input
                value={contactPhone}
                onChange={(event) => setContactPhone(event.target.value)}
                placeholder="+1 (917) 555-0199"
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeContactModal}>
                Cancel
              </button>

              <button type="button" onClick={saveContact}>
                Save Contact
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default EditProfile;
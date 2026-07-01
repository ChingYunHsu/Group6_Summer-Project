import { useState } from "react";
import "./EditProfile.css";
import { useNavigate } from "react-router-dom";
import {
  USER_PROFILE,
  EMERGENCY_CONTACTS,
} from "../data/userProfile";

function EditProfile() {
  const navigate = useNavigate();

  const [allergies, setAllergies] = useState(USER_PROFILE.allergies);
  const [conditions, setConditions] = useState(USER_PROFILE.medical_conditions);

  const [contacts, setContacts] = useState(EMERGENCY_CONTACTS);

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

  function openConditionModal() {
    setConditionName("");
    setConditionDetail("");
    setEditingConditionIndex(null);
    setShowConditionModal(true);
  }

  function editCondition(index) {
    setConditionName(conditions[index].name);
    setConditionDetail(conditions[index].detail);
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
      name: conditionName,
      detail: conditionDetail || "No details provided",
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
    setAllergyName(allergies[index].name);
    setAllergyDetail(allergies[index].detail);
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
      name: allergyName,
      detail: allergyDetail || "No details provided",
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
    setContactName(contacts[index].name);
    setContactRelationship(contacts[index].relationship);
    setContactPhone(contacts[index].phone);
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
      name: contactName,
      relationship: contactRelationship || "Emergency Contact",
      phone: contactPhone || "No phone provided",
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

  return (
    <main className="edit-profile-page">
      <h1>Edit Personal & Medical Profile</h1>
      <p className="edit-subtitle">
        Update your core identity, vital signs, and clinical history for accurate care routing.
      </p>

      <section className="edit-section">
        <h2>▣ Core Identity</h2>

        <div className="core-grid">
          <div className="edit-avatar"></div>

          <label>
            Full Name
            <input defaultValue={USER_PROFILE.full_name} />
          </label>

          <label>
            Date of Birth
            <input type="date" defaultValue={USER_PROFILE.date_of_birth} />
          </label>

          <label>
            Gender
            <select defaultValue={USER_PROFILE.gender}>
              <option>Female</option>
              <option>Male</option>
              <option>Other</option>
            </select>
          </label>

        </div>
      </section>

      <section className="edit-section">
        <h2>♡ Vital Signs</h2>
        <label>
          Blood Type
          <select defaultValue={USER_PROFILE.blood_type}>
            <option>O Positive (O+)</option>
            <option>O Negative (O-)</option>
            <option>A Positive (A+)</option>
            <option>A Negative (A-)</option>
            <option>B Positive (B+)</option>
            <option>AB Positive (AB+)</option>
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

            {allergies.map((allergy, index) => (
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
            ))}
          </div>

          <div>
            <div className="section-line-title">
              <h3>Medical Conditions</h3>
              <button type="button" onClick={openConditionModal}>
                + Add Condition
              </button>
            </div>

            {conditions.map((condition, index) => (
              <div className="editable-item" key={`${condition.name}-${index}`}>
                <div>
                  <strong>{condition.name}</strong>
                  <p>{condition.detail}</p>
                </div>

                <div className="item-actions">
                  <button type="button" onClick={() => editCondition(index)}>
                    ✏️
                  </button>

                  <button type="button" onClick={() => deleteCondition(index)}>
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="edit-section">
        <h2>▣ Contact Information</h2>

        <div className="contact-form-grid">
          <label>
            Phone Number
            <input defaultValue={USER_PROFILE.phone} />
          </label>

          <label>
            Email Address
            <input defaultValue={USER_PROFILE.email} />
          </label>
        </div>

        <label>
          Primary Address
          <textarea defaultValue={USER_PROFILE.address} />
        </label>

        <div className="section-line-title emergency-title-row">
          <h3>Emergency Contacts</h3>
          <button type="button" onClick={openContactModal}>
            + Add Contact
          </button>
        </div>

        <div className="contact-row-list">
          {contacts.map((contact, index) => (
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
          ))}
        </div>

        <div className="edit-footer">
          <button type="button" onClick={() => navigate("/profile")}>
            Discard Changes
          </button>
          <button type="button" onClick={() => navigate("/profile")}>
            Save Profile
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
                onChange={(event) => setContactRelationship(event.target.value)}
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
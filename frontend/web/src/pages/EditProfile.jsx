import { useEffect, useState } from "react";
import "./EditProfile.css";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  getMedicalProfile,
  updateMedicalProfile,
} from "../services/MedicalProfileApi";

import {
  getUserProfile,
  updateUserProfile,
} from "../services/UserProfileApi";

const SUPPORTED_LANGUAGES = [
  { value: "English", label: "English" },
  { value: "French", label: "French / Français" },
  { value: "Spanish", label: "Spanish / Español" },
  { value: "Chinese", label: "Chinese / 中文" },
  { value: "Italian", label: "Italian / Italiano" },
];

const LANGUAGE_ALIASES = {
  en: "English",
  english: "English",
  fr: "French",
  french: "French",
  français: "French",
  francais: "French",
  es: "Spanish",
  spanish: "Spanish",
  español: "Spanish",
  espanol: "Spanish",
  zh: "Chinese",
  chinese: "Chinese",
  mandarin: "Chinese",
  中文: "Chinese",
  it: "Italian",
  italian: "Italian",
  italiano: "Italian",
};

function normaliseSupportedLanguage(value) {
  const cleanedValue = String(value ?? "")
    .trim()
    .toLowerCase();

  return LANGUAGE_ALIASES[cleanedValue] ?? "";
}

const NATIONALITY_OPTIONS = [
  "American",
  "Australian",
  "Austrian",
  "Belgian",
  "Brazilian",
  "British",
  "Bulgarian",
  "Canadian",
  "Chilean",
  "Chinese",
  "Colombian",
  "Croatian",
  "Cypriot",
  "Czech",
  "Danish",
  "Dutch",
  "Egyptian",
  "Estonian",
  "Finnish",
  "French",
  "German",
  "Greek",
  "Hungarian",
  "Icelandic",
  "Indian",
  "Indonesian",
  "Irish",
  "Israeli",
  "Italian",
  "Japanese",
  "Kenyan",
  "Latvian",
  "Lithuanian",
  "Luxembourgish",
  "Malaysian",
  "Maltese",
  "Mexican",
  "Moroccan",
  "New Zealander",
  "Nigerian",
  "Norwegian",
  "Pakistani",
  "Peruvian",
  "Filipino",
  "Polish",
  "Portuguese",
  "Romanian",
  "Saudi Arabian",
  "Singaporean",
  "Slovak",
  "Slovenian",
  "South African",
  "South Korean",
  "Spanish",
  "Swedish",
  "Swiss",
  "Thai",
  "Turkish",
  "Ukrainian",
  "Emirati",
  "Vietnamese",
];

const BLOOD_TYPE_OPTIONS = [
  { value: "O+", key: "oPositive" },
  { value: "O-", key: "oNegative" },
  { value: "A+", key: "aPositive" },
  { value: "A-", key: "aNegative" },
  { value: "B+", key: "bPositive" },
  { value: "B-", key: "bNegative" },
  { value: "AB+", key: "abPositive" },
  { value: "AB-", key: "abNegative" },
];

function EditProfile() {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  const [form, setForm] = useState({
    full_name: "",
    date_of_birth: "",
    gender: "",
    blood_type: "",
    phone: "",
    email: "",
    nationality: "",
    primary_language: "",
    secondary_language: "",
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
              .map(normaliseSupportedLanguage)
              .filter(Boolean)
              .slice(0, 2)
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
          primary_language: spokenLanguages[0] || "",
          secondary_language: spokenLanguages[1] || "",
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
        setError(error.message || t("editProfile.couldNotLoadProfile"));
      } finally {
        setIsLoading(false);
      }
    }

    loadProfile();
  }, [t]);

  function updateFormField(fieldName, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [fieldName]: value,
    }));
  }

  function getSpokenLanguagesArray() {
    return [form.primary_language, form.secondary_language]
      .map((language) => language.trim())
      .filter(
        (language, index, languages) =>
          language && languages.indexOf(language) === index
      );
  }

  function updatePrimaryLanguage(value) {
    setForm((currentForm) => ({
      ...currentForm,
      primary_language: value,
      secondary_language:
        currentForm.secondary_language === value
          ? ""
          : currentForm.secondary_language,
    }));
  }

  function updateSecondaryLanguage(value) {
    setForm((currentForm) => ({
      ...currentForm,
      secondary_language:
        value === currentForm.primary_language ? "" : value,
    }));
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
        phone: form.phone.trim(),
        nationality: form.nationality.trim(),
        spoken_languages: getSpokenLanguagesArray(),
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
        : error.message || t("editProfile.couldNotSaveProfile");

      setError(message);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <main className="edit-profile-page">
        <p>{t("editProfile.loading")}</p>
      </main>
    );
  }

  return (
    <main className="edit-profile-page">
      <h1>{t("editProfile.pageTitle")}</h1>

      <p className="edit-subtitle">
        {t("editProfile.subtitle")}
      </p>

      {error && <p className="profile-error">{error}</p>}

      <section className="edit-section">
        <h2>▣ {t("editProfile.coreIdentity")}</h2>

        <div className="core-grid">
          <div className="edit-avatar"></div>

          <label>
            {t("editProfile.fullName")}
            <input value={form.full_name} readOnly />
          </label>

          <label>
            {t("editProfile.dateOfBirth")}
            <input
              type="date"
              value={form.date_of_birth}
              onChange={(event) =>
                updateFormField("date_of_birth", event.target.value)
              }
            />
          </label>

          <label>
            {t("editProfile.gender")}
            <select
              value={form.gender}
              onChange={(event) =>
                updateFormField("gender", event.target.value)
              }
            >
              <option value="">{t("editProfile.selectGender")}</option>
              <option value="Female">{t("editProfile.genderFemale")}</option>
              <option value="Male">{t("editProfile.genderMale")}</option>
              <option value="Other">{t("editProfile.genderOther")}</option>
            </select>
          </label>

          <label>
            {t("editProfile.nationality")}
            <select
              value={form.nationality}
              onChange={(event) =>
                updateFormField("nationality", event.target.value)
              }
            >
              <option value="">{t("editProfile.selectNationality")}</option>

              {form.nationality &&
                !NATIONALITY_OPTIONS.includes(form.nationality) && (
                  <option value={form.nationality}>
                    {form.nationality}
                  </option>
                )}

              {NATIONALITY_OPTIONS.map((nationality) => (
                <option key={nationality} value={nationality}>
                  {t(`editProfile.nationalities.${nationality}`, {
                    defaultValue: nationality,
                  })}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="edit-section">
        <h2>♡ {t("editProfile.vitalSigns")}</h2>

        <label>
          {t("editProfile.bloodType")}
          <select
            value={form.blood_type}
            onChange={(event) =>
              updateFormField("blood_type", event.target.value)
            }
          >
            <option value="">{t("medicalId.selectBloodType")}</option>
            {BLOOD_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {t(`editProfile.bloodTypes.${option.key}`)}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="edit-section">
        <h2>▣ {t("editProfile.clinicalProfile")}</h2>

        <div className="two-column-edit">
          <div>
            <div className="section-line-title">
              <h3>{t("editProfile.allergiesHeading")}</h3>

              <button type="button" onClick={openAllergyModal}>
                + {t("medicalId.addAllergy")}
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
              <p>{t("editProfile.noAllergiesAdded")}</p>
            )}
          </div>

          <div>
            <div className="section-line-title">
              <h3>{t("medicalId.medicalConditions")}</h3>

              <button type="button" onClick={openConditionModal}>
                + {t("medicalId.addCondition")}
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
              <p>{t("editProfile.noConditionsAdded")}</p>
            )}
          </div>
        </div>
      </section>

      <section className="edit-section">
        <h2>▣ {t("editProfile.contactInformation")}</h2>

        <div className="contact-form-grid">
          <label>
            {t("editProfile.phoneNumber")}
            <input
              value={form.phone}
              onChange={(event) =>
                updateFormField("phone", event.target.value)
              }
            />
          </label>

          <label>
            {t("editProfile.emailAddress")}
            <input type="email" value={form.email} readOnly />
          </label>
        </div>

        <div className="contact-form-grid language-select-grid">
          <label>
            {t("editProfile.primaryLanguage")}
            <select
              value={form.primary_language}
              onChange={(event) =>
                updatePrimaryLanguage(event.target.value)
              }
            >
              <option value="">{t("editProfile.selectPrimaryLanguage")}</option>


              {SUPPORTED_LANGUAGES.map((language) => (
                <option
                  key={language.value}
                  value={language.value}
                  disabled={
                    language.value === form.secondary_language
                  }
                >
                  {t(`editProfile.languageOptions.${language.value}`, {
                    defaultValue: language.label,
                  })}
                </option>
              ))}
            </select>
          </label>

          <label>
            {t("editProfile.secondaryLanguage")}
            <select
              value={form.secondary_language}
              onChange={(event) =>
                updateSecondaryLanguage(event.target.value)
              }
            >
              <option value="">{t("editProfile.noSecondaryLanguage")}</option>


              {SUPPORTED_LANGUAGES.map((language) => (
                <option
                  key={language.value}
                  value={language.value}
                  disabled={language.value === form.primary_language}
                >
                  {t(`editProfile.languageOptions.${language.value}`, {
                    defaultValue: language.label,
                  })}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="language-helper-text">
          {t("editProfile.languageHelperText")}
        </p>

        <label>
          {t("editProfile.primaryAddress")}
          <textarea
            value={form.address}
            onChange={(event) =>
              updateFormField("address", event.target.value)
            }
          />
        </label>

        <div className="section-line-title emergency-title-row">
          <h3>{t("editProfile.emergencyContactsHeading")}</h3>

          <button type="button" onClick={openContactModal}>
            + {t("editProfile.addContact")}
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
            <p>{t("editProfile.noContactsAdded")}</p>
          )}
        </div>

        <div className="edit-footer">
          <button type="button" onClick={() => navigate("/profile")}>
            {t("editProfile.discardChanges")}
          </button>

          <button
            type="button"
            onClick={handleSaveProfile}
            disabled={isSaving}
          >
            {isSaving ? t("common.saving") : t("editProfile.saveProfile")}
          </button>
        </div>
      </section>

      {showConditionModal && (
        <div className="edit-modal-overlay">
          <div className="edit-modal">
            <h2>
              {editingConditionIndex !== null
                ? t("editProfile.editConditionTitle")
                : t("editProfile.addConditionTitle")}
            </h2>

            <label>
              {t("editProfile.conditionNameLabel")}
              <input
                value={conditionName}
                onChange={(event) => setConditionName(event.target.value)}
                placeholder={t("editProfile.conditionNamePlaceholder")}
              />
            </label>

            <label>
              {t("editProfile.conditionDescriptionLabel")}
              <textarea
                value={conditionDetail}
                onChange={(event) => setConditionDetail(event.target.value)}
                placeholder={t("editProfile.conditionDescriptionPlaceholder")}
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeConditionModal}>
                {t("common.cancel")}
              </button>

              <button type="button" onClick={saveCondition}>
                {t("editProfile.saveCondition")}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAllergyModal && (
        <div className="edit-modal-overlay">
          <div className="edit-modal">
            <h2>
              {editingAllergyIndex !== null
                ? t("editProfile.editAllergyTitle")
                : t("editProfile.addAllergyTitle")}
            </h2>

            <label>
              {t("editProfile.allergyNameLabel")}
              <input
                value={allergyName}
                onChange={(event) => setAllergyName(event.target.value)}
                placeholder={t("editProfile.allergyNamePlaceholder")}
              />
            </label>

            <label>
              {t("editProfile.allergyDetailLabel")}
              <textarea
                value={allergyDetail}
                onChange={(event) => setAllergyDetail(event.target.value)}
                placeholder={t("editProfile.allergyDetailPlaceholder")}
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeAllergyModal}>
                {t("common.cancel")}
              </button>

              <button type="button" onClick={saveAllergy}>
                {t("editProfile.saveAllergy")}
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
                ? t("editProfile.editContactTitle")
                : t("editProfile.addContactTitle")}
            </h2>

            <label>
              {t("editProfile.contactNameLabel")}
              <input
                value={contactName}
                onChange={(event) => setContactName(event.target.value)}
                placeholder={t("editProfile.contactNamePlaceholder")}
              />
            </label>

            <label>
              {t("editProfile.contactRelationshipLabel")}
              <input
                value={contactRelationship}
                onChange={(event) =>
                  setContactRelationship(event.target.value)
                }
                placeholder={t("editProfile.contactRelationshipPlaceholder")}
              />
            </label>

            <label>
              {t("editProfile.phoneNumber")}
              <input
                value={contactPhone}
                onChange={(event) => setContactPhone(event.target.value)}
                placeholder={t("editProfile.contactPhonePlaceholder")}
              />
            </label>

            <div className="edit-modal-actions">
              <button type="button" onClick={closeContactModal}>
                {t("common.cancel")}
              </button>

              <button type="button" onClick={saveContact}>
                {t("editProfile.saveContact")}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default EditProfile;

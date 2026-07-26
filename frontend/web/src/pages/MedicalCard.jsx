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

const LANGUAGE_ALIASES = {
  en: "en",
  english: "en",
  "english (english)": "en",

  fr: "fr",
  french: "fr",
  français: "fr",
  francais: "fr",
  "français (french)": "fr",

  es: "es",
  spanish: "es",
  español: "es",
  espanol: "es",
  "español (spanish)": "es",

  zh: "zh",
  chinese: "zh",
  mandarin: "zh",
  中文: "zh",
  "中文 (chinese)": "zh",

  it: "it",
  italian: "it",
  italiano: "it",
  "italiano (italian)": "it",
};

const MEDICAL_PASSPORT_TRANSLATIONS = {
  fr: {
    languageName: "French",
    localLanguageName: "Français",
    direction: "ltr",
    medicalAlert: "ALERTE MÉDICALE",
    name: "NOM",
    blood: "GROUPE SANGUIN",
    allergies: "ALLERGIES",
    medicalConditions: "PROBLÈMES MÉDICAUX",
    personalInfo: "INFORMATIONS PERSONNELLES",
    dateOfBirth: "DATE DE NAISSANCE",
    nationality: "NATIONALITÉ",
    gender: "GENRE",
    phone: "TÉLÉPHONE",
    address: "ADRESSE",
    emergency: "URGENCE",
    notProvided: "Non renseigné",
    bloodNotAvailable: "Non disponible",
    noAllergies: "Aucune allergie connue indiquée.",
    noConditions: "Aucun problème médical indiqué.",
    noEmergencyContact: "Aucun contact d’urgence indiqué.",
    phoneNotProvided: "Numéro de téléphone non renseigné",
  },

  es: {
    languageName: "Spanish",
    localLanguageName: "Español",
    direction: "ltr",
    medicalAlert: "ALERTA MÉDICA",
    name: "NOMBRE",
    blood: "SANGRE",
    allergies: "ALERGIAS",
    medicalConditions: "CONDICIONES MÉDICAS",
    personalInfo: "INFORMACIÓN PERSONAL",
    dateOfBirth: "FECHA DE NACIMIENTO",
    nationality: "NACIONALIDAD",
    gender: "GÉNERO",
    phone: "TELÉFONO",
    address: "DIRECCIÓN",
    emergency: "EMERGENCIA",
    notProvided: "No proporcionado",
    bloodNotAvailable: "No disponible",
    noAllergies: "No se han indicado alergias conocidas.",
    noConditions: "No se han indicado condiciones médicas.",
    noEmergencyContact: "No se ha indicado un contacto de emergencia.",
    phoneNotProvided: "Número de teléfono no proporcionado",
  },

  zh: {
    languageName: "Chinese",
    localLanguageName: "中文",
    direction: "ltr",
    medicalAlert: "医疗警示",
    name: "姓名",
    blood: "血型",
    allergies: "过敏信息",
    medicalConditions: "健康状况",
    personalInfo: "个人信息",
    dateOfBirth: "出生日期",
    nationality: "国籍",
    gender: "性别",
    phone: "电话",
    address: "地址",
    emergency: "紧急联系人",
    notProvided: "未提供",
    bloodNotAvailable: "暂无信息",
    noAllergies: "未列出已知过敏信息。",
    noConditions: "未列出健康状况。",
    noEmergencyContact: "未列出紧急联系人。",
    phoneNotProvided: "未提供电话号码",
  },

  it: {
    languageName: "Italian",
    localLanguageName: "Italiano",
    direction: "ltr",
    medicalAlert: "ALLERTA MEDICA",
    name: "NOME",
    blood: "GRUPPO SANGUIGNO",
    allergies: "ALLERGIE",
    medicalConditions: "CONDIZIONI MEDICHE",
    personalInfo: "INFORMAZIONI PERSONALI",
    dateOfBirth: "DATA DI NASCITA",
    nationality: "NAZIONALITÀ",
    gender: "GENERE",
    phone: "TELEFONO",
    address: "INDIRIZZO",
    emergency: "EMERGENZA",
    notProvided: "Non fornito",
    bloodNotAvailable: "Non disponibile",
    noAllergies: "Nessuna allergia nota indicata.",
    noConditions: "Nessuna condizione medica indicata.",
    noEmergencyContact: "Nessun contatto di emergenza indicato.",
    phoneNotProvided: "Numero di telefono non fornito",
  },
};

function normaliseList(value) {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value !== "string") {
    return [];
  }

  try {
    const parsedValue = JSON.parse(value);

    if (Array.isArray(parsedValue)) {
      return parsedValue;
    }
  } catch {
    // Fall through to comma-separated parsing.
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normaliseLanguageCode(value) {
  const cleanedValue = String(value ?? "")
    .trim()
    .toLowerCase();

  return LANGUAGE_ALIASES[cleanedValue] ?? cleanedValue;
}

function getPreferredSecondaryLanguage(spokenLanguages) {
  const languages = normaliseList(spokenLanguages);

  // English is always shown. Use the first saved non-English language.
  for (const language of languages) {
    const languageCode = normaliseLanguageCode(language);

    if (languageCode && languageCode !== "en") {
      return {
        code: languageCode,
        originalValue: String(language).trim(),
      };
    }
  }

  return null;
}

function normaliseProfile(userProfile = {}, medicalProfile = {}) {
  const allergies = normaliseList(medicalProfile.allergies);

  const medicalConditions = Array.isArray(
    medicalProfile.medical_conditions
  )
    ? medicalProfile.medical_conditions
    : normaliseList(medicalProfile.conditions);

  const emergencyContacts = Array.isArray(
    medicalProfile.emergency_contacts
  )
    ? medicalProfile.emergency_contacts
    : [];

  const spokenLanguages = normaliseList(
    userProfile.spoken_languages ?? medicalProfile.spoken_languages
  );

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

    email: userProfile.email || medicalProfile.email || "",
    phone: userProfile.phone || medicalProfile.phone || "",
    nationality:
      userProfile.nationality || medicalProfile.nationality || "",
    spoken_languages: spokenLanguages,
    date_of_birth: medicalProfile.date_of_birth || "",
    gender: medicalProfile.gender || "",
    blood_type: medicalProfile.blood_type || "",
    address: medicalProfile.address || userProfile.address || "",
    allergies,
    medical_conditions: medicalConditions,
    conditions: medicalConditions,
    emergency_contacts: emergencyContacts,
    medications: normaliseList(medicalProfile.medications),
  };
}

function getClinicalItemName(item) {
  if (typeof item === "string") {
    return item;
  }

  return item?.name ?? "";
}

function getClinicalItemDetail(item) {
  if (!item || typeof item === "string") {
    return "";
  }

  return item.detail ?? item.description ?? "";
}

function BilingualText({
  english,
  translated,
  languageCode,
  direction = "ltr",
}) {
  return (
    <>
      <span lang="en">{english}</span>

      {translated && (
        <>
          <span aria-hidden="true"> / </span>
          <span lang={languageCode} dir={direction}>
            {translated}
          </span>
        </>
      )}
    </>
  );
}

function MedicalCard() {
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPreparingPrint, setIsPreparingPrint] = useState(false);
  const [error, setError] = useState("");

  const loadProfile = useCallback(async () => {
    const [userProfile, medicalProfile] = await Promise.all([
      getUserProfile(),
      getMedicalProfile(),
    ]);

    const combinedProfile = normaliseProfile(
      userProfile,
      medicalProfile
    );

    setProfile(combinedProfile);
    return combinedProfile;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initialisePage() {
      try {
        setIsLoading(true);
        setError("");
        await loadProfile();
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        console.error(
          "Failed to load medical card profile:",
          loadError
        );

        setError(
          loadError.message || "Could not load medical profile."
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void initialisePage();

    return () => {
      cancelled = true;
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
          {error || "No medical profile available."}
        </p>
      </main>
    );
  }

  const allergies = Array.isArray(profile.allergies)
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
    emergencyContacts.find((contact) => contact?.primary) ||
    emergencyContacts[0] ||
    null;

  const selectedSecondaryLanguage =
    getPreferredSecondaryLanguage(profile.spoken_languages);

  const secondaryLanguageCode =
    selectedSecondaryLanguage?.code ?? null;

  const secondaryTranslation = secondaryLanguageCode
    ? MEDICAL_PASSPORT_TRANSLATIONS[secondaryLanguageCode] ?? null
    : null;

  const secondaryDirection =
    secondaryTranslation?.direction ?? "ltr";

  const fallbackValue = (
    <BilingualText
      english="Not provided"
      translated={secondaryTranslation?.notProvided}
      languageCode={secondaryLanguageCode}
      direction={secondaryDirection}
    />
  );

  return (
    <main className="medical-card-page">
      <section className="medical-preview-header print-hide">
        <h1>Medical Document Preview</h1>

        <p>
          Review your critical health information before generating a
          printable A4 emergency document.
        </p>

        {secondaryTranslation && (
          <p className="medical-language-status">
            Passport language: English and{" "}
            <strong>
              {secondaryTranslation.localLanguageName}
            </strong>
          </p>
        )}

        {!selectedSecondaryLanguage && (
          <p className="medical-language-notice" role="status">
            No secondary spoken language has been selected. The
            Medical Passport will be displayed in English only.
          </p>
        )}

        {selectedSecondaryLanguage && !secondaryTranslation && (
          <p className="medical-language-notice" role="status">
            A Medical Passport translation is not currently available
            for{" "}
            <strong>
              {selectedSecondaryLanguage.originalValue}
            </strong>
            . Emergency information will be displayed in English only.
          </p>
        )}
      </section>

      {error && (
        <p className="medical-error print-hide">{error}</p>
      )}

      <section className="medical-a4-canvas">
        <header className="medical-alert-header">
          <div>
            <h2 lang="en">MEDICAL ALERT</h2>

            {secondaryTranslation && (
              <span
                lang={secondaryLanguageCode}
                dir={secondaryDirection}
              >
                {secondaryTranslation.medicalAlert}
              </span>
            )}
          </div>

          <div
            className="medical-cross-icon"
            aria-hidden="true"
          >
            ✚
          </div>
        </header>

        {!secondaryTranslation && (
          <p className="medical-language-notice" role="status">
            {selectedSecondaryLanguage
              ? `Translation unavailable for ${selectedSecondaryLanguage.originalValue}. English emergency information is shown.`
              : "No secondary spoken language selected. English emergency information is shown."}
          </p>
        )}

        <section className="medical-card-body">
          <div className="medical-top-grid">
            <div>
              <span className="medical-label">
                <BilingualText
                  english="NAME"
                  translated={secondaryTranslation?.name}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </span>

              <h3>
                {profile.full_name ||
                  profile.display_name ||
                  fallbackValue}
              </h3>
            </div>

            <div className="blood-preview">
              <span className="medical-label">
                <BilingualText
                  english="BLOOD"
                  translated={secondaryTranslation?.blood}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </span>

              <strong>
                {profile.blood_type || (
                  <BilingualText
                    english="N/A"
                    translated={
                      secondaryTranslation?.bloodNotAvailable
                    }
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                )}
              </strong>

              <small>{profile.donor_status || ""}</small>
            </div>
          </div>

          <div className="medical-section-grid">
            <div>
              <h4>
                <BilingualText
                  english="ALLERGIES"
                  translated={secondaryTranslation?.allergies}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </h4>

              {allergies.length > 0 ? (
                allergies.map((allergy, index) => {
                  const allergyName =
                    getClinicalItemName(allergy);
                  const allergyDetail =
                    getClinicalItemDetail(allergy);

                  return (
                    <div
                      className="medical-alert-item red-item"
                      key={allergyName || `allergy-${index}`}
                    >
                      <div className="medical-alert-item-content">
                        <strong>
                          {allergyName || fallbackValue}
                        </strong>

                        {allergyDetail && <p>{allergyDetail}</p>}
                      </div>
                    </div>
                  );
                })
              ) : (
                <p>
                  <BilingualText
                    english="No known allergies listed."
                    translated={
                      secondaryTranslation?.noAllergies
                    }
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                </p>
              )}
            </div>

            <div>
              <h4>
                <BilingualText
                  english="MEDICAL CONDITIONS"
                  translated={
                    secondaryTranslation?.medicalConditions
                  }
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </h4>

              {medicalConditions.length > 0 ? (
                medicalConditions.map((condition, index) => {
                  const conditionName =
                    getClinicalItemName(condition);
                  const conditionDetail =
                    getClinicalItemDetail(condition);

                  return (
                    <div
                      className="medical-alert-item blue-item"
                      key={
                        conditionName || `condition-${index}`
                      }
                    >
                      <div className="medical-alert-item-content">
                        <strong>
                          {conditionName || fallbackValue}
                        </strong>

                        {conditionDetail && (
                          <p>{conditionDetail}</p>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <p>
                  <BilingualText
                    english="No medical conditions listed."
                    translated={
                      secondaryTranslation?.noConditions
                    }
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                </p>
              )}
            </div>
          </div>

          <div className="medical-bottom-grid">
            <div>
              <h4>
                <BilingualText
                  english="PERSONAL INFO"
                  translated={secondaryTranslation?.personalInfo}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </h4>

              <p>
                <strong>
                  <BilingualText
                    english="DOB"
                    translated={secondaryTranslation?.dateOfBirth}
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                  :
                </strong>{" "}
                {profile.date_of_birth || fallbackValue}
              </p>

              <p>
                <strong>
                  <BilingualText
                    english="Nationality"
                    translated={secondaryTranslation?.nationality}
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                  :
                </strong>{" "}
                {profile.nationality || fallbackValue}
              </p>

              <p>
                <strong>
                  <BilingualText
                    english="Gender"
                    translated={secondaryTranslation?.gender}
                    languageCode={secondaryLanguageCode}
                    direction={secondaryDirection}
                  />
                  :
                </strong>{" "}
                {profile.gender || fallbackValue}
              </p>

              <h4>
                <BilingualText
                  english="PHONE"
                  translated={secondaryTranslation?.phone}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </h4>

              <p>{profile.phone || fallbackValue}</p>
            </div>

            <div>
              <h4>
                <BilingualText
                  english="ADDRESS"
                  translated={secondaryTranslation?.address}
                  languageCode={secondaryLanguageCode}
                  direction={secondaryDirection}
                />
              </h4>

              <p>{profile.address || fallbackValue}</p>

              {primaryContact ? (
                <div className="emergency-contact-card">
                  <h4>
                    <BilingualText
                      english="EMERGENCY"
                      translated={secondaryTranslation?.emergency}
                      languageCode={secondaryLanguageCode}
                      direction={secondaryDirection}
                    />
                  </h4>

                  <strong>
                    {primaryContact.name || fallbackValue}
                  </strong>

                  <p>
                    {primaryContact.relationship || fallbackValue}
                  </p>

                  {primaryContact.phone ? (
                    <a href={`tel:${primaryContact.phone}`}>
                      {primaryContact.phone}
                    </a>
                  ) : (
                    <p>
                      <BilingualText
                        english="Phone not provided"
                        translated={
                          secondaryTranslation?.phoneNotProvided
                        }
                        languageCode={secondaryLanguageCode}
                        direction={secondaryDirection}
                      />
                    </p>
                  )}
                </div>
              ) : (
                <div className="emergency-contact-card">
                  <h4>
                    <BilingualText
                      english="EMERGENCY"
                      translated={secondaryTranslation?.emergency}
                      languageCode={secondaryLanguageCode}
                      direction={secondaryDirection}
                    />
                  </h4>

                  <p>
                    <BilingualText
                      english="No emergency contact listed."
                      translated={
                        secondaryTranslation?.noEmergencyContact
                      }
                      languageCode={secondaryLanguageCode}
                      direction={secondaryDirection}
                    />
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
        ⓘ Designed for standard A4 document size: 210mm × 297mm
      </p>
    </main>
  );
}

export default MedicalCard;
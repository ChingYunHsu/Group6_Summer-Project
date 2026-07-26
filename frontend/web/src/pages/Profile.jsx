import {
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  getMedicalProfile,
} from "../services/MedicalProfileApi";
import {
  getUserProfile,
} from "../services/UserProfileApi";

import {
  getGenderEmoji,
  notifyProfileAvatarUpdated,
  PROFILE_GENDER_KEY,
  PROFILE_PHOTO_KEY,
  resizeProfilePhoto,
} from "../utils/profileAvatar";

import "./Profile.css";

function Profile() {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  const photoInputRef = useRef(null);

  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] =
    useState(true);
  const [error, setError] = useState("");

  const [profilePhoto, setProfilePhoto] =
    useState(() => {
      return (
        localStorage.getItem(
          PROFILE_PHOTO_KEY
        ) || ""
      );
    });

  const [photoError, setPhotoError] =
    useState("");

  useEffect(() => {
    async function loadProfile() {
      try {
        setIsLoading(true);
        setError("");

        const [
          userProfileResponse,
          medicalProfileResponse,
        ] = await Promise.all([
          getUserProfile(),
          getMedicalProfile(),
        ]);

        const userProfile =
          userProfileResponse ?? {};

        const medicalProfile =
          medicalProfileResponse ?? {};

        console.log(
          "USER PROFILE RESPONSE:",
          userProfile
        );

        console.log(
          "MEDICAL PROFILE RESPONSE:",
          medicalProfile
        );

        const combinedProfile = {
          ...medicalProfile,
          ...userProfile,

          /*
           * Keep medical profile versions of medical
           * and personal health fields when available.
           */
          date_of_birth:
            medicalProfile.date_of_birth ||
            userProfile.date_of_birth ||
            "",

          gender:
            medicalProfile.gender ||
            userProfile.gender ||
            "",

          address:
            medicalProfile.address ||
            userProfile.address ||
            "",

          blood_type:
            medicalProfile.blood_type || "",

          allergies: Array.isArray(
            medicalProfile.allergies
          )
            ? medicalProfile.allergies
            : [],

          medical_conditions: Array.isArray(
            medicalProfile.medical_conditions
          )
            ? medicalProfile.medical_conditions
            : Array.isArray(
                  medicalProfile.conditions
                )
              ? medicalProfile.conditions
              : [],

          emergency_contacts: Array.isArray(
            medicalProfile.emergency_contacts
          )
            ? medicalProfile.emergency_contacts
            : [],

          spoken_languages: Array.isArray(
            userProfile.spoken_languages
          )
            ? userProfile.spoken_languages
            : [],
        };

        setProfile(combinedProfile);

        localStorage.setItem(
          PROFILE_GENDER_KEY,
          combinedProfile.gender || "other"
        );

        notifyProfileAvatarUpdated();
      } catch (loadError) {
        console.error(
          "Failed to load profile:",
          loadError
        );

        setError(
          loadError.message ||
            t("profile.couldNotLoadProfile")
        );
      } finally {
        setIsLoading(false);
      }
    }

    void loadProfile();
  }, [t]);

  async function handleProfilePhotoChange(
    event
  ) {
    const file = event.target.files?.[0];

    /*
     * Reset the value so the same file can be
     * selected again later.
     */
    event.target.value = "";

    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setPhotoError(
        t("profile.invalidPhotoType", {
          defaultValue:
            "Please choose an image file.",
        })
      );

      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setPhotoError(
        t("profile.photoTooLarge", {
          defaultValue:
            "Please choose an image smaller than 8 MB.",
        })
      );

      return;
    }

    try {
      setPhotoError("");

      const resizedPhoto =
        await resizeProfilePhoto(file);

      localStorage.setItem(
        PROFILE_PHOTO_KEY,
        resizedPhoto
      );

      setProfilePhoto(resizedPhoto);
      notifyProfileAvatarUpdated();
    } catch (uploadError) {
      console.error(
        "Failed to save profile photo:",
        uploadError
      );

      setPhotoError(
        uploadError.message ||
          t("profile.photoUploadFailed", {
            defaultValue:
              "The profile photo could not be saved.",
          })
      );
    }
  }

  function handleRemoveProfilePhoto() {
    localStorage.removeItem(
      PROFILE_PHOTO_KEY
    );

    setProfilePhoto("");
    setPhotoError("");

    notifyProfileAvatarUpdated();
  }

  if (isLoading) {
    return (
      <main className="profile-page">
        <p>{t("profile.loadingProfile")}</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="profile-page">
        <p className="profile-error">
          {error ||
            t("profile.noProfileAvailable")}
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

  const spokenLanguages = Array.isArray(
    profile.spoken_languages
  )
    ? profile.spoken_languages
    : [];

  return (
    <main className="profile-page">
      <div className="profile-title-row">
        <div>
          <h1>{t("profile.pageTitle")}</h1>

          <p>
            {t("profile.pageDescription")}
          </p>
        </div>

        <div className="profile-actions">
          <button
            type="button"
            onClick={() =>
              navigate("/profile/edit")
            }
          >
            ✎ {t("profile.editCta")}
          </button>

          <button
            type="button"
            onClick={() =>
              navigate("/medical-card", {
                state: {
                  medicalCardPayload: profile,
                },
              })
            }
          >
            ⎙ {t("profile.printMedicalCard")}
          </button>
        </div>
      </div>

      <section className="profile-grid">
        <aside className="profile-left">
          <div className="profile-card identity-card">
            <div
              className={
                profilePhoto
                  ? "avatar-box avatar-box--photo"
                  : "avatar-box"
              }
            >
              {profilePhoto ? (
                <img
                  src={profilePhoto}
                  alt={t(
                    "profile.profilePhotoAlt",
                    {
                      defaultValue:
                        "Profile photograph",
                    }
                  )}
                />
              ) : (
                <span aria-hidden="true">
                  {getGenderEmoji(
                    profile.gender
                  )}
                </span>
              )}
            </div>

            <input
              ref={photoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hidden
              onChange={
                handleProfilePhotoChange
              }
            />

            <div className="profile-photo-actions">
              <button
                type="button"
                onClick={() =>
                  photoInputRef.current?.click()
                }
              >
                {profilePhoto
                  ? t(
                      "profile.changePhoto",
                      {
                        defaultValue:
                          "Change photo",
                      }
                    )
                  : t(
                      "profile.addPhoto",
                      {
                        defaultValue:
                          "Add photo",
                      }
                    )}
              </button>

              {profilePhoto && (
                <button
                  type="button"
                  className="remove-profile-photo"
                  onClick={
                    handleRemoveProfilePhoto
                  }
                >
                  {t(
                    "profile.removePhoto",
                    {
                      defaultValue:
                        "Remove",
                    }
                  )}
                </button>
              )}
            </div>

            {photoError && (
              <p
                className="profile-photo-error"
                role="alert"
              >
                {photoError}
              </p>
            )}

            <h2>
              {profile.full_name ||
                profile.display_name ||
                profile.email ||
                t("profile.notProvided")}
            </h2>

            <span className="verified-badge">
              ⊙ {t("profile.verifiedPatient")}
            </span>

            <div className="info-line">
              <span>
                {t("profile.dobLabel")}
              </span>

              <strong>
                {profile.date_of_birth ||
                  t("profile.notProvided")}
              </strong>
            </div>

            <div className="info-line">
              <span>
                {t("profile.gender")}
              </span>

              <strong>
                {profile.gender ||
                  t("profile.notProvided")}
              </strong>
            </div>

            <div className="info-line">
              <span>
                {t("profile.nationality")}
              </span>

              <strong>
                {profile.nationality ||
                  t("profile.notProvided")}
              </strong>
            </div>
          </div>

          <div className="profile-card">
            <h3>
              ▧{" "}
              {t(
                "profile.contactInformationHeading"
              )}
            </h3>

            <p>
              <strong>
                {t(
                  "profile.phoneNumberLabel"
                )}
              </strong>
              <br />
              {profile.phone ||
                t("profile.notProvided")}
            </p>

            <p>
              <strong>
                {t(
                  "profile.emailAddressLabel"
                )}
              </strong>
              <br />
              {profile.email ||
                t("profile.notProvided")}
            </p>

            <p>
              <strong>
                {t(
                  "profile.primaryAddressLabel"
                )}
              </strong>
              <br />
              {profile.address ||
                t("profile.notProvided")}
            </p>
          </div>
        </aside>

        <section className="profile-right">
          <div className="top-cards">
            <div className="profile-card vital-card">
              <h3>
                {t(
                  "profile.vitalSignsHeading"
                )}
              </h3>

              <div className="blood-row">
                <span className="blood-type">
                  {profile.blood_type ||
                    t(
                      "profile.notAvailableShort"
                    )}
                </span>

                <p>
                  <strong>
                    {t(
                      "profile.bloodTypeLabel"
                    )}
                  </strong>
                </p>
              </div>
            </div>

            <div className="profile-card language-card">
              <h3>
                {t(
                  "profile.spokenLanguagesHeading"
                )}
              </h3>

              <div className="tag-list">
                {spokenLanguages.length > 0 ? (
                  spokenLanguages.map(
                    (language) => (
                      <span key={language}>
                        {language}
                      </span>
                    )
                  )
                ) : (
                  <p>
                    {t(
                      "profile.notProvided"
                    )}
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="profile-card clinical-card">
            <h2>
              ▣{" "}
              {t(
                "profile.clinicalProfileHeading"
              )}
            </h2>

            <div className="clinical-columns">
              <div>
                <h3 className="warning-heading">
                  △{" "}
                  {t(
                    "profile.allergiesHeading"
                  )}
                </h3>

                {allergies.length > 0 ? (
                  allergies.map(
                    (allergy, index) => (
                      <div
                        className="medical-item red-dot"
                        key={
                          allergy.name ||
                          allergy ||
                          index
                        }
                      >
                        <strong>
                          {allergy.name ||
                            allergy}
                        </strong>

                        <p>
                          {allergy.detail || ""}
                        </p>
                      </div>
                    )
                  )
                ) : (
                  <p>
                    {t(
                      "profile.noAllergiesListed"
                    )}
                  </p>
                )}
              </div>

              <div>
                <h3 className="condition-heading">
                  ⌘{" "}
                  {t(
                    "profile.medicalConditionsHeading"
                  )}
                </h3>

                {medicalConditions.length >
                0 ? (
                  medicalConditions.map(
                    (condition, index) => (
                      <div
                        className="medical-item blue-dot"
                        key={
                          condition.name ||
                          condition ||
                          index
                        }
                      >
                        <strong>
                          {condition.name ||
                            condition}
                        </strong>

                        <p>
                          {condition.detail || ""}
                        </p>
                      </div>
                    )
                  )
                ) : (
                  <p>
                    {t(
                      "profile.noConditionsListed"
                    )}
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="profile-card">
            <h2>
              ✱{" "}
              {t(
                "profile.emergencyContactsHeading"
              )}
            </h2>

            <div className="contacts-grid">
              {emergencyContacts.length > 0 ? (
                emergencyContacts.map(
                  (contact, index) => (
                    <div
                      className="contact-box"
                      key={
                        contact.name ||
                        contact.phone ||
                        index
                      }
                    >
                      <div className="contact-top">
                        <strong>
                          {contact.name ||
                            t(
                              "profile.notProvided"
                            )}
                        </strong>

                        {contact.primary && (
                          <span>
                            {t(
                              "profile.primaryTag"
                            )}
                          </span>
                        )}
                      </div>

                      <p>
                        {contact.relationship ||
                          t(
                            "profile.notProvided"
                          )}
                      </p>

                      <p>
                        {contact.phone ||
                          t(
                            "profile.notProvided"
                          )}
                      </p>
                    </div>
                  )
                )
              ) : (
                <p>
                  {t(
                    "profile.noContactsListed"
                  )}
                </p>
              )}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

export default Profile;
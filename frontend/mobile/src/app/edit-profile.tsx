import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { allLanguages } from "../data/languages";
import { mockProfile } from "../data/mockProfile";
import { loadMedicalId, saveMedicalId } from "../services/medicalIdService";
import { loadProfile, saveProfile } from "../services/profileService";

// No real endpoint returns anything like avatar_initials — it was always
// mockProfile.avatar_initials regardless of which real user was logged
// in. Derived from the live full_name instead, so it actually reflects
// whoever's account this is.
function getInitials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function EditProfileScreen() {
  const { t } = useTranslation();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [fullName, setFullName] = useState(mockProfile.full_name);
  const [dob, setDob] = useState(mockProfile.date_of_birth);
  const [gender, setGender] = useState(mockProfile.gender);
  const [nationality, setNationality] = useState(mockProfile.nationality);
  const [phone, setPhone] = useState(mockProfile.phone);
  const [email, setEmail] = useState(mockProfile.email);
  const [address, setAddress] = useState("");
  const [spokenLanguages, setSpokenLanguages] = useState<string[]>(
    mockProfile.spoken_languages,
  );

  const [languageModalVisible, setLanguageModalVisible] = useState(false);
  const [languageSearch, setLanguageSearch] = useState("");

  const [genderModalVisible, setGenderModalVisible] = useState(false);

  const genderOptions = [
    {
      value: "Male",
      label: t("editProfile.genderMale", { defaultValue: "Male" }),
    },
    {
      value: "Female",
      label: t("editProfile.genderFemale", { defaultValue: "Female" }),
    },
    {
      value: "Non-binary",
      label: t("editProfile.genderNonBinary", { defaultValue: "Non-binary" }),
    },
    {
      value: "Prefer not to say",
      label: t("editProfile.genderPreferNotToSay", {
        defaultValue: "Prefer not to say",
      }),
    },
  ];

  const filteredLanguageOptions = useMemo(() => {
    if (!languageSearch.trim()) return [];

    return allLanguages.filter(
      (language) =>
        !spokenLanguages.some(
          (item) => item.toLowerCase() === language.english.toLowerCase(),
        ) &&
        (language.native.toLowerCase().includes(languageSearch.toLowerCase()) ||
          language.english
            .toLowerCase()
            .includes(languageSearch.toLowerCase())),
    );
  }, [languageSearch, spokenLanguages]);

  useEffect(() => {
    (async () => {
      try {
        const [profile, medical] = await Promise.all([
          loadProfile().catch((error) => {
            console.error("Failed to load profile", error);
            return null;
          }),
          loadMedicalId().catch((error) => {
            console.error("Failed to load medical profile", error);
            return null;
          }),
        ]);

        if (profile) {
          setFullName(profile.full_name);
          setEmail(profile.email);
          setPhone(profile.phone);
          setNationality(profile.nationality);
          setSpokenLanguages(profile.spoken_languages ?? []);
        }

        if (medical) {
          if (medical.gender) setGender(medical.gender);
          if (medical.address) setAddress(medical.address);
          if (medical.date_of_birth) setDob(medical.date_of_birth);
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSave = async () => {
    setSaving(true);

    const results = await Promise.allSettled([
      saveProfile({
        phone,
        nationality,
        spoken_languages: spokenLanguages,
      }),
      saveMedicalId({ date_of_birth: dob, gender, address }),
    ]);

    setSaving(false);

    const failed = results.some((result) => result.status === "rejected");

    if (failed) {
      results.forEach((result) => {
        if (result.status === "rejected") {
          console.error("Failed to save profile field", result.reason);
        }
      });

      Alert.alert(
        t("editProfile.saveErrorTitle", {
          defaultValue: "Couldn't save everything",
        }),
        t("editProfile.saveErrorMessage", {
          defaultValue: "Some of your changes didn't save. Please try again.",
        }),
      );

      return;
    }

    router.back();
  };

  const removeLanguage = (language: string) => {
    setSpokenLanguages(spokenLanguages.filter((item) => item !== language));
  };

  const addLanguage = (language: { native: string; english: string }) => {
    setSpokenLanguages([...spokenLanguages, language.english]);
    setLanguageSearch("");
    setLanguageModalVisible(false);
  };

  const selectGender = (value: string) => {
    setGender(value);
    setGenderModalVisible(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={24} color={Colours.text} />
          </TouchableOpacity>

          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>{t("editProfile.title")}</Text>
          </View>

          <TouchableOpacity
            testID="edit-profile-save-button"
            onPress={handleSave}
            disabled={loading || saving}
          >
            <Text
              style={[
                styles.saveText,
                (loading || saving) && styles.saveTextDisabled,
              ]}
            >
              {saving
                ? t("common.saving", { defaultValue: "Saving…" })
                : t("common.save")}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarInitials}>{getInitials(fullName)}</Text>
          </View>

          <Text style={styles.avatarName}>{fullName}</Text>

          <Text style={styles.avatarSubtext}>
            {t("editProfile.personalProfile")}
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            {t("editProfile.personalInformation")}
          </Text>

          <InputField
            testID="edit-profile-fullname-input"
            label={t("editProfile.fullName")}
            value={fullName}
            editable={false}
          />

          <InputField
            testID="edit-profile-dob-input"
            label={t("editProfile.dateOfBirth")}
            value={dob}
            onChangeText={setDob}
            placeholder="YYYY-MM-DD"
          />

          <View style={styles.field}>
            <Text style={styles.label}>{t("editProfile.gender")}</Text>

            <TouchableOpacity
              testID="edit-profile-gender-trigger"
              style={[styles.input, styles.pickerTrigger]}
              onPress={() => setGenderModalVisible(true)}
            >
              <Text
                style={
                  gender ? styles.pickerValueText : styles.pickerPlaceholderText
                }
              >
                {gender ||
                  t("editProfile.selectGender", {
                    defaultValue: "Select gender",
                  })}
              </Text>
            </TouchableOpacity>
          </View>

          <InputField
            testID="edit-profile-nationality-input"
            label={t("editProfile.nationality")}
            value={nationality}
            onChangeText={setNationality}
          />

          <InputField
            testID="edit-profile-phone-input"
            label={t("editProfile.phoneNumber")}
            value={phone}
            onChangeText={setPhone}
          />

          <InputField
            testID="edit-profile-email-input"
            label={t("editProfile.emailAddress")}
            value={email}
            editable={false}
            keyboardType="email-address"
          />

          <InputField
            testID="edit-profile-address-input"
            label={t("editProfile.address")}
            value={address}
            onChangeText={setAddress}
            multiline
          />

          <View style={styles.tagSectionHeader}>
            <Text style={styles.label}>{t("editProfile.spokenLanguages")}</Text>

            <TouchableOpacity
              testID="edit-profile-add-language-button"
              onPress={() => setLanguageModalVisible(true)}
            >
              <Ionicons name="add-circle" size={24} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {spokenLanguages.map((language) => (
              <View key={language} style={styles.tag}>
                <Text style={styles.tagText}>{language}</Text>

                <TouchableOpacity
                  testID={`edit-profile-remove-language-${language}`}
                  onPress={() => removeLanguage(language)}
                >
                  <Ionicons name="close" size={16} color={Colours.muted} />
                </TouchableOpacity>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>

      <Modal visible={languageModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {t("editProfile.addLanguage", {
                defaultValue: "Add Language",
              })}
            </Text>

            <TextInput
              testID="edit-profile-language-search-input"
              style={styles.modalInput}
              value={languageSearch}
              onChangeText={setLanguageSearch}
              placeholder={t("editProfile.languagePlaceholder", {
                defaultValue: "Search languages...",
              })}
              placeholderTextColor={Colours.muted}
              autoFocus
            />

            {languageSearch.length > 0 && (
              <ScrollView style={styles.pickerResultsList}>
                {filteredLanguageOptions.map((language) => (
                  <TouchableOpacity
                    key={language.english}
                    testID={`edit-profile-language-option-${language.english}`}
                    style={styles.pickerResultRow}
                    onPress={() => addLanguage(language)}
                  >
                    <Text style={styles.pickerResultText}>
                      {language.native} ({language.english})
                    </Text>
                  </TouchableOpacity>
                ))}

                {filteredLanguageOptions.length === 0 && (
                  <Text style={styles.pickerEmptyText}>
                    {t("editProfile.noLanguageMatches", {
                      defaultValue: "No matches found.",
                    })}
                  </Text>
                )}
              </ScrollView>
            )}

            <View style={styles.modalActions}>
              <TouchableOpacity
                testID="edit-profile-language-cancel-button"
                onPress={() => {
                  setLanguageSearch("");
                  setLanguageModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={genderModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {t("editProfile.selectGender", {
                defaultValue: "Select gender",
              })}
            </Text>

            {genderOptions.map((option) => (
              <TouchableOpacity
                key={option.value}
                testID={`edit-profile-gender-option-${option.value}`}
                style={styles.pickerResultRow}
                onPress={() => selectGender(option.value)}
              >
                <Text style={styles.pickerResultText}>{option.label}</Text>

                {gender === option.value && (
                  <Ionicons
                    name="checkmark"
                    size={20}
                    color={Colours.primary}
                  />
                )}
              </TouchableOpacity>
            ))}

            <View style={styles.modalActions}>
              <TouchableOpacity
                testID="edit-profile-gender-cancel-button"
                onPress={() => setGenderModalVisible(false)}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function InputField({
  label,
  value,
  onChangeText = () => {},
  multiline = false,
  keyboardType = "default",
  editable = true,
  placeholder,
  testID,
}: {
  label: string;
  value: string;
  onChangeText?: (text: string) => void;
  multiline?: boolean;
  editable?: boolean;
  keyboardType?: "default" | "email-address" | "phone-pad";
  placeholder?: string;
  testID?: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>

      <TextInput
        testID={testID}
        style={[styles.input, multiline && styles.multilineInput]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        editable={editable}
        keyboardType={keyboardType}
        placeholder={placeholder}
        placeholderTextColor={Colours.muted}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  content: {
    padding: 20,
    paddingBottom: 60,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 24,
  },

  headerTitle: {
    ...Typography.h3,
    color: Colours.text,
    textAlign: "center",
  },

  saveText: {
    color: Colours.primary,
    fontWeight: "700",
    fontSize: 16,
  },

  saveTextDisabled: {
    opacity: 0.4,
  },

  avatarSection: {
    alignItems: "center",
    marginBottom: 32,
  },

  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },

  avatarName: {
    ...Typography.h3,
    color: Colours.text,
  },

  avatarSubtext: {
    color: Colours.muted,
    marginTop: 4,
  },

  section: {
    backgroundColor: Colours.surface,
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 24,
  },

  sectionTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 20,
  },

  field: {
    marginBottom: 18,
  },

  label: {
    color: Colours.muted,
    marginBottom: 8,
    fontSize: 12,
    fontWeight: "600",
  },

  input: {
    height: 56,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 14,
    paddingHorizontal: 16,
    backgroundColor: Colours.surface,
    color: Colours.text,
    fontSize: 16,
  },

  multilineInput: {
    height: undefined,
    minHeight: 100,
    paddingTop: 14,
    textAlignVertical: "top",
  },

  avatarInitials: {
    fontSize: 32,
    fontWeight: "700",
    color: Colours.primary,
  },

  tagSectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },

  tagRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginBottom: 18,
  },

  tag: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },

  tagText: {
    marginRight: 6,
    color: Colours.text,
  },

  modalOverlay: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
  },

  modalCard: {
    width: "85%",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 20,
  },

  modalTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 16,
  },

  modalInput: {
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },

  modalActions: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  pickerTrigger: {
    justifyContent: "center",
  },

  pickerValueText: {
    color: Colours.text,
    fontSize: 16,
  },

  pickerPlaceholderText: {
    color: Colours.muted,
    fontSize: 16,
  },

  pickerResultsList: {
    maxHeight: 250,
    marginBottom: 12,
  },

  pickerResultRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  pickerResultText: {
    ...Typography.body,
    color: Colours.text,
  },

  pickerEmptyText: {
    color: Colours.muted,
    textAlign: "center",
    paddingVertical: 20,
  },
});

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
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
  const [newLanguage, setNewLanguage] = useState("");

  // Profile (phone/nationality/spoken_languages — the `users` table) and
  // medical (gender/address/etc. — `medical_profiles`) are two separate
  // backend resources, per user.py's get_user_profile / medicalIdService's
  // get_medical_profile. Loaded in parallel; either can fail independently
  // without blocking the other from populating.
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
      // NOTE: as of this writing, PUT /user/medical-profile in user.py is
      // shadowed by a second implementation that only accepts
      // {blood_type, conditions, allergies} — gender/address will 400
      // ("invalid_fields") until the team resolves which implementation
      // (user.py vs api/medical.py) is meant to stay. This call is correct
      // for the intended backend behaviour; it just won't succeed until
      // that's fixed server-side.
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

  const addLanguage = () => {
    const value = newLanguage.trim();

    if (!value) {
      return;
    }

    if (
      spokenLanguages.some((item) => item.toLowerCase() === value.toLowerCase())
    ) {
      return;
    }

    setSpokenLanguages([...spokenLanguages, value]);

    setNewLanguage("");
    setLanguageModalVisible(false);
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

          <TouchableOpacity onPress={handleSave} disabled={loading || saving}>
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
            label={t("editProfile.fullName")}
            value={fullName}
            editable={false}
          />

          <InputField
            label={t("editProfile.dateOfBirth")}
            value={dob}
            onChangeText={setDob}
            placeholder="YYYY-MM-DD"
          />

          <InputField
            label={t("editProfile.gender")}
            value={gender}
            onChangeText={setGender}
          />

          <InputField
            label={t("editProfile.nationality")}
            value={nationality}
            onChangeText={setNationality}
          />

          <InputField
            label={t("editProfile.phoneNumber")}
            value={phone}
            onChangeText={setPhone}
          />

          <InputField
            label={t("editProfile.emailAddress")}
            value={email}
            editable={false}
            keyboardType="email-address"
          />

          <InputField
            label={t("editProfile.address")}
            value={address}
            onChangeText={setAddress}
            multiline
          />

          <View style={styles.tagSectionHeader}>
            <Text style={styles.label}>{t("editProfile.spokenLanguages")}</Text>

            <TouchableOpacity onPress={() => setLanguageModalVisible(true)}>
              <Ionicons name="add-circle" size={24} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {spokenLanguages.map((language) => (
              <View key={language} style={styles.tag}>
                <Text style={styles.tagText}>{language}</Text>

                <TouchableOpacity onPress={() => removeLanguage(language)}>
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
              style={styles.modalInput}
              value={newLanguage}
              onChangeText={setNewLanguage}
              placeholder={t("editProfile.languagePlaceholder", {
                defaultValue: "Enter language",
              })}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => {
                  setNewLanguage("");
                  setLanguageModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={addLanguage}>
                <Text>{t("common.add")}</Text>
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
}: {
  label: string;
  value: string;
  onChangeText?: (text: string) => void;
  multiline?: boolean;
  editable?: boolean;
  keyboardType?: "default" | "email-address" | "phone-pad";
  placeholder?: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>

      <TextInput
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
});

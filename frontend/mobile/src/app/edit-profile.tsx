import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
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
import { saveProfile } from "../services/profileService";

export default function EditProfileScreen() {
  const { t } = useTranslation(); 

  const [fullName, setFullName] =
    useState(mockProfile.full_name);

  const [dob, setDob] =
    useState(mockProfile.date_of_birth);

  const [gender, setGender] =
    useState(mockProfile.gender);

  const [nationality, setNationality] =
    useState("American");

  const [phone, setPhone] =
    useState(mockProfile.phone);

  const [email, setEmail] =
    useState(mockProfile.email);

  const [address, setAddress] =
    useState(
      "1234 Sycamore Lane, Apt 4B, San Francisco, CA 94105"
    );

  const [spokenLanguages, setSpokenLanguages] =
  useState(
    mockProfile.spoken_languages.join(", ")
  );

const handleSave = async () => {
  try {
    await saveProfile({
      phone,
      nationality,
      spoken_languages: spokenLanguages
        .split(",")
        .map((lang) => lang.trim())
        .filter(Boolean),
    });

    router.back();
  } catch (error) {
    console.error(
      "Failed to save profile",
      error
    );
  }
};

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
          >
            <Ionicons
              name="chevron-back"
              size={24}
              color={Colours.text}
            />
          </TouchableOpacity>

          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>
  {t("editProfile.title")}
</Text>
          </View>

          <TouchableOpacity
            onPress={handleSave}
          >
            <Text style={styles.saveText}>
  {t("common.save")}
</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarInitials}>
             {mockProfile.avatar_initials}
            </Text>
        </View>

          <Text style={styles.avatarName}>
            {fullName}
          </Text>

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
            editable={false}
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
            label={t("editProfile.email")}
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

          <InputField
            label={t("editProfile.spokenLanguages")}
            value={spokenLanguages}
            onChangeText={setSpokenLanguages}
          />
      </View>

    </ScrollView>
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
}: {
  label: string;
  value: string;
  onChangeText?: (text: string) => void;
  multiline?: boolean;
  editable?: boolean;
  keyboardType?:
    | "default"
    | "email-address"
    | "phone-pad";
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>
        {label}
      </Text>

      <TextInput
        style={[
          styles.input,
          multiline &&
            styles.multilineInput,
        ]}
        value={value}
        onChangeText={onChangeText}
        multiline={multiline}
        editable={editable}
        keyboardType={keyboardType}
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

  avatarSection: {
    alignItems: "center",
    marginBottom: 32,
  },

  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor:
      Colours.surfaceLight,
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
    backgroundColor:
      Colours.surface,
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
    backgroundColor:
      Colours.surface,
    color: Colours.text,
    fontSize: 16,
  },

  multilineInput: {
    minHeight: 100,
    paddingTop: 14,
    textAlignVertical: "top",
  },

  avatarInitials: {
    fontSize: 32,
    fontWeight: "700",
    color: Colours.primary,
  }
});
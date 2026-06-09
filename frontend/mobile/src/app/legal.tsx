import Checkbox from "expo-checkbox";
import { useRouter } from "expo-router";
import { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function LegalScreen() {
  const router = useRouter();

  const [acceptedTerms, setAcceptedTerms] =
    useState(false);

  const [acceptedPrivacy, setAcceptedPrivacy] =
    useState(false);

  const canContinue =
    acceptedTerms && acceptedPrivacy;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={true}
      >
        <Text style={styles.title}>
          Legal & Privacy
        </Text>

        <Text style={styles.heading}>
          Review Agreements
        </Text>

        <Text style={styles.subtitle}>
          Please review our updated terms and
          privacy practices to continue.
        </Text>

        {/* TERMS */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>
            📄 Terms of Service
          </Text>

          <Text style={styles.cardDescription}>
            Governs your use of our platform
            and services.
          </Text>

          <View style={styles.previewBox}>
  <ScrollView
    nestedScrollEnabled
    showsVerticalScrollIndicator
    style={styles.previewScroll}
  >
    <Text style={styles.previewText}>
      1. Acceptance of Terms{"\n\n"}
      By accessing this application,
      you agree to be bound by these
      Terms of Service.
      {"\n\n"}
      2. User Responsibilities{"\n\n"}
      You are responsible for
      maintaining the confidentiality
      of your account information.
      {"\n\n"}
      3. Service Availability{"\n\n"}
      We strive for 99.9% uptime but
      do not guarantee uninterrupted
      access.
      {"\n\n"}
      4. Modifications{"\n\n"}
      We reserve the right to modify
      these terms at any time with
      prior notice.
      {"\n\n"}
      5. Account Security{"\n\n"}
      Users must take reasonable
      steps to protect login
      credentials and account access.
      {"\n\n"}
      6. Limitation of Liability{"\n\n"}
      We are not liable for losses
      resulting from misuse of the
      platform or interruptions
      outside our control.
    </Text>
  </ScrollView>
</View>
        </View>

        <View style={styles.checkboxRow}>
          <Checkbox
            value={acceptedTerms}
            onValueChange={setAcceptedTerms}
            color={
              acceptedTerms
                ? Colours.primary
                : undefined
            }
          />

          <Text style={styles.checkboxText}>
            I agree to the Terms of Service
          </Text>
        </View>

        {/* PRIVACY */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>
            🛡 Privacy Policy
          </Text>

          <Text style={styles.cardDescription}>
            Details how we protect and manage
            your data.
          </Text>

          <View style={styles.securityBox}>
            <Text style={styles.securityText}>
              🔒 All sensitive health data is
              secured with 256-bit HIPAA
              compliant encryption.
            </Text>
          </View>

          <View style={styles.previewBox}>
  <ScrollView
    nestedScrollEnabled
    showsVerticalScrollIndicator
    style={styles.previewScroll}
  >
    <Text style={styles.previewText}>
      1. Data Collection{"\n\n"}
      We collect minimal data
      necessary to provide our
      services, including location
      data for nearby clinic mapping.
      {"\n\n"}
      2. Data Usage{"\n\n"}
      Your data is used strictly for
      improving service delivery and
      personalization.
      {"\n\n"}
      3. Third-Party Sharing{"\n\n"}
      We never sell your personal
      data. Data is only shared with
      authorized medical partners
      when you request an
      appointment.
      {"\n\n"}
      4. Your Rights{"\n\n"}
      You have the right to access,
      modify, or delete your data at
      any time.
      {"\n\n"}
      5. Data Retention{"\n\n"}
      We retain only the information
      required to provide services
      and comply with legal
      obligations.
      {"\n\n"}
      6. Security Measures{"\n\n"}
      All sensitive medical
      information is encrypted and
      protected using industry
      standard security practices.
    </Text>
  </ScrollView>
</View>
        </View>

        <View style={styles.checkboxRow}>
          <Checkbox
            value={acceptedPrivacy}
            onValueChange={setAcceptedPrivacy}
            color={
              acceptedPrivacy
                ? Colours.primary
                : undefined
            }
          />

          <Text style={styles.checkboxText}>
            I agree to the Privacy Policy
          </Text>
        </View>

        <TouchableOpacity
          disabled={!canContinue}
          style={[
            styles.button,
            !canContinue &&
              styles.disabledButton,
          ]}
          onPress={() =>
            router.push("/location")
          }
        >
          <Text
            style={[
              styles.buttonText,
              !canContinue &&
                styles.disabledButtonText,
            ]}
          >
            Accept & Continue
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  scrollView: {
    flex: 1,
  },

  content: {
    padding: 20,
    paddingBottom: 60,
  },

  title: {
    ...Typography.h2,
    color: Colours.text,
    marginTop: 12,
    marginBottom: 24,
  },

  heading: {
    ...Typography.h3,
    color: Colours.text,
    marginBottom: 8,
  },

  subtitle: {
    ...Typography.bodySmall,
    color: Colours.muted,
    lineHeight: 22,
    marginBottom: 28,
  },

  card: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: Colours.borderLight,
  },

  cardTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: Colours.text,
    marginBottom: 6,
  },

  cardDescription: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginBottom: 14,
  },

  previewBox: {
    backgroundColor: Colours.surface,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderColor: Colours.border,
  },

  previewScroll: {
    height: 140,
  },

  previewText: {
    ...Typography.bodySmall,
    color: Colours.text,
    lineHeight: 20,
  },

  securityBox: {
    backgroundColor: "#E8F5E9",
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
  },

  securityText: {
    color: "#166534",
    fontWeight: "600",
    lineHeight: 20,
  },

  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 28,
    gap: 12,
  },

  checkboxText: {
    ...Typography.bodySmall,
    color: Colours.text,
    flex: 1,
  },

  button: {
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    marginBottom: 40,
  },

  disabledButton: {
    backgroundColor: Colours.border,
  },

  buttonText: {
    ...Typography.button,
    color: Colours.surface,
    textAlign: "center",
  },

  disabledButtonText: {
    color: Colours.disabled,
  },
});
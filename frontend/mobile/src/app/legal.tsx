import Checkbox from "expo-checkbox";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function LegalScreen() {
  const router = useRouter();

  const { t } = useTranslation();

  // Onboarding (welcome.tsx) opens this screen with no params — default
  // behavior unchanged, Accept & Continue pushes forward to /location.
  // Opened mid-session (the More tab's "Legal" row) passes origin="app",
  // so Accept & Continue returns to wherever the user actually came from
  // instead of restarting the rest of onboarding underneath them.
  const { origin } = useLocalSearchParams<{ origin?: string }>();
  const isInAppEntry = origin === "app";

  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);

  const canContinue = acceptedTerms && acceptedPrivacy;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={true}
      >
        <Text style={styles.title}>{t("legal.title")}</Text>

        <Text style={styles.heading}>{t("legal.reviewHeading")}</Text>

        <Text style={styles.subtitle}>{t("legal.reviewSubtitle")}</Text>

        {/* TERMS */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📄 {t("legal.terms")}</Text>

          <Text style={styles.cardDescription}>
            {t("legal.termsDescription")}
          </Text>

          <View style={styles.previewBox}>
            <ScrollView
              nestedScrollEnabled
              showsVerticalScrollIndicator
              style={styles.previewScroll}
            >
              <Text style={styles.previewText}>{t("legal.termsPreview")}</Text>
            </ScrollView>
          </View>
        </View>

        <View style={styles.checkboxRow}>
          <Checkbox
            testID="terms-checkbox"
            value={acceptedTerms}
            onValueChange={setAcceptedTerms}
            color={acceptedTerms ? Colours.primary : undefined}
          />

          <Text style={styles.checkboxText}>{t("legal.agreeTerms")}</Text>
        </View>

        {/* PRIVACY */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>🛡 {t("legal.privacy")}</Text>

          <Text style={styles.cardDescription}>
            {t("legal.privacyDescription")}
          </Text>

          <View style={styles.securityBox}>
            <Text style={styles.securityText}>
              🔒 {t("legal.securityNotice")}
            </Text>
          </View>

          <View style={styles.previewBox}>
            <ScrollView
              nestedScrollEnabled
              showsVerticalScrollIndicator
              style={styles.previewScroll}
            >
              <Text style={styles.previewText}>
                {t("legal.privacyPreview")}
              </Text>
            </ScrollView>
          </View>
        </View>

        <View style={styles.checkboxRow}>
          <Checkbox
            testID="privacy-checkbox"
            value={acceptedPrivacy}
            onValueChange={setAcceptedPrivacy}
            color={acceptedPrivacy ? Colours.primary : undefined}
          />

          <Text style={styles.checkboxText}>{t("legal.agreePrivacy")}</Text>
        </View>

        <TouchableOpacity
          testID="continue-button"
          disabled={!canContinue}
          style={[styles.button, !canContinue && styles.disabledButton]}
          onPress={() => {
            if (isInAppEntry) {
              router.back();
            } else {
              router.push("/location");
            }
          }}
        >
          <Text
            style={[
              styles.buttonText,
              !canContinue && styles.disabledButtonText,
            ]}
          >
            {t("legal.acceptContinue")}
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
    height: 200,
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

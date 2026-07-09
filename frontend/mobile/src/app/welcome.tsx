import { useLocalSearchParams, useRouter } from "expo-router";
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { useTranslation } from "react-i18next";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function WelcomeScreen() {
  const router = useRouter();
  const { t } = useTranslation();

  // Onboarding (legal.tsx, arriving from language.tsx) opens this screen
  // with no params — default behavior unchanged, Continue pushes forward
  // to /legal. Opened mid-session (the More tab's "Welcome" row) passes
  // origin="app", so Continue returns to wherever the user actually came
  // from instead of restarting the rest of onboarding underneath them.
  const { origin } = useLocalSearchParams<{ origin?: string }>();
  const isInAppEntry = origin === "app";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <Image
        source={require("../../assets/images/clearpath-logo.png")}
        style={styles.logo}
      />

      <Text style={styles.title}>ClearPath</Text>

      <Text style={styles.slogan}>{t("welcome.slogan")}</Text>

      <View style={styles.card}>
        <Text style={styles.featureTitle}>
          🧭 {t("welcome.healthcareNavigation")}
        </Text>

        <Text style={styles.featureText}>
          {t("welcome.healthcareNavigationDescription")}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.featureTitle}>🪪 {t("welcome.medicalId")}</Text>

        <Text style={styles.featureText}>
          {t("welcome.medicalIdDescription")}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.featureTitle}>🤖 {t("welcome.aiAssistant")}</Text>

        <Text style={styles.featureText}>
          {t("welcome.aiAssistantDescription")}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.featureTitle}>💬 {t("welcome.showStaff")}</Text>

        <Text style={styles.featureText}>
          {t("welcome.showStaffDescription")}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.featureTitle}>🚨 {t("welcome.emergencySos")}</Text>

        <Text style={styles.featureText}>
          {t("welcome.emergencySosDescription")}
        </Text>
      </View>

      <TouchableOpacity
        style={styles.button}
        onPress={() => {
          if (isInAppEntry) {
            router.back();
          } else {
            router.push("/legal");
          }
        }}
      >
        <Text style={styles.buttonText}>
          {isInAppEntry
            ? t("common.done", { defaultValue: "Done" })
            : t("common.continue")}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#1F5BFF",
  },

  content: {
    padding: 24,
    paddingTop: 70,
    paddingBottom: 40,
  },

  logo: {
    width: 240,
    height: 240,
    alignSelf: "center",
    resizeMode: "contain",
    marginBottom: 40,
  },

  title: {
    ...Typography.h1,
    color: "#FFFFFF",
    textAlign: "center",
    marginBottom: 10,
  },

  card: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  featureTitle: {
    ...Typography.h3,
    color: Colours.text,
    marginBottom: 8,
  },

  featureText: {
    ...Typography.body,
    color: Colours.muted,
  },

  button: {
    backgroundColor: "#FFFFFF",
    borderRadius: 30,
    paddingVertical: 18,
    padding: 18,
    marginTop: 20,
  },

  buttonText: {
    ...Typography.button,
    color: Colours.primary,
    textAlign: "center",
  },

  slogan: {
    ...Typography.h3,
    color: "#FFFFFF",
    textAlign: "center",
    marginBottom: 12,
  },

  description: {
    ...Typography.body,
    color: "rgba(255,255,255,0.85)",
    textAlign: "center",
  },
});

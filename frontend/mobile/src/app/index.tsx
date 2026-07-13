import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function Index() {
  const router = useRouter();
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Image
          source={require("../../assets/images/clearpath-logo.png")}
          style={styles.logo}
        />

        <Text style={styles.title}>ClearPath</Text>

        <Text style={styles.slogan}>
          Accessibility Intelligence in your language
        </Text>

        <Text style={styles.description}>
          Helping patients to easily find healthcare services and accessible
          facilities.
        </Text>
      </View>

      <TouchableOpacity
        style={styles.button}
        onPress={() => router.push("/language")}
      >
        <Text style={styles.buttonText}>
          {t("common.getStarted", { defaultValue: "Get Started" })}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.surface,
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingTop: 80,
    paddingBottom: 50,
  },

  content: {
    alignItems: "center",
  },

  logo: {
    width: 200,
    height: 200,
    resizeMode: "contain",
    marginBottom: 32,
  },

  title: {
    ...Typography.h1,
    color: Colours.text,
    textAlign: "center",
    marginBottom: 16,
  },

  slogan: {
    fontSize: 22,
    fontWeight: "700",
    color: Colours.primary,
    textAlign: "center",
    marginBottom: 20,
  },

  description: {
    ...Typography.body,
    color: Colours.muted,
    textAlign: "center",
    lineHeight: 26,
    paddingHorizontal: 10,
  },

  button: {
    backgroundColor: Colours.primary,
    borderRadius: 30,
    paddingVertical: 18,
    alignItems: "center",
  },

  buttonText: {
    ...Typography.button,
    color: Colours.surface,
  },
});

import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";
import { getAccessToken } from "../../services/authService";

// Simple menu screen linking out to account, language, settings, legal,
// welcome, and SOS. Layout/behaviour is otherwise static — the only
// dynamic bit is whether the top row says "Log In / Register" (guest)
// or opens Settings directly (already logged in).
export default function MoreScreen() {
  const router = useRouter();
  const { t } = useTranslation();

  // Whether the user currently has no auth token — determines what the
  // top row does when tapped.
  const [isGuest, setIsGuest] = useState(false);

  // Checks auth status once on mount so the top row's destination is
  // correct on first render.
  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();
        setIsGuest(!token);
      } catch (error) {
        console.error("Failed to check auth status for More screen", error);
        setIsGuest(true);
      }
    })();
  }, []);

  return (
    <View style={styles.container}>
      <TouchableOpacity
        testID="more-login-register-row"
        style={styles.item}
        onPress={() => router.push(isGuest ? "/login" : "/settings")}
      >
        <Text style={styles.text}>
          🔑 {t("more.loginRegister", { defaultValue: "Log In / Register" })}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        testID="more-language-row"
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/language", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>💬 {t("more.languageSelection")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        testID="more-settings-row"
        style={styles.item}
        onPress={() => router.push("/settings")}
      >
        <Text style={styles.text}>⚙️ {t("more.settings")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        testID="more-legal-row"
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/legal", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>📄 {t("more.legal")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        testID="more-welcome-row"
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/welcome", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>👋 {t("more.welcome")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        testID="more-sos-row"
        style={styles.item}
        onPress={() => router.push("/sos")}
      >
        <Text style={styles.text}>🚨 {t("more.sos")}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.surface,
    padding: 20,
  },

  item: {
    paddingVertical: 18,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  text: {
    ...Typography.body,
    color: Colours.text,
    fontWeight: "600",
  },
});

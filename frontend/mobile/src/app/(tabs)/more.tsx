import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";
import { getAccessToken } from "../../services/authService";

export default function MoreScreen() {
  const router = useRouter();
  const { t } = useTranslation();

  // Guests had no way to create an account anywhere except stumbling onto
  // the Profile tab's locked wall — this gives a second, more discoverable
  // path. Row stays visible either way rather than disappearing when
  // logged in (a shifting menu can look broken) — label/destination just
  // adapt: guest -> /login, logged in -> /settings (where logout lives).
  const [isGuest, setIsGuest] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();
        setIsGuest(!token);
      } catch (error) {
        // Erring toward showing the login option rather than hiding it —
        // worse to hide a needed login path than to show one
        // unnecessarily to someone who's actually logged in.
        console.error("Failed to check auth status for More screen", error);
        setIsGuest(true);
      }
    })();
  }, []);

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.item}
        onPress={() => router.push(isGuest ? "/login" : "/settings")}
      >
        <Text style={styles.text}>
          🔑 {t("more.loginRegister", { defaultValue: "Log In / Register" })}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/language", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>💬 {t("more.languageSelection")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.item}
        onPress={() => router.push("/settings")}
      >
        <Text style={styles.text}>⚙️ {t("more.settings")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/legal", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>📄 {t("more.legal")}</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.item}
        onPress={() =>
          router.push({ pathname: "/welcome", params: { origin: "app" } })
        }
      >
        <Text style={styles.text}>👋 {t("more.welcome")}</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.item} onPress={() => router.push("/sos")}>
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

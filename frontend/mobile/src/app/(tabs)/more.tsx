import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";

export default function MoreScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  return (
    <View style={styles.container}>
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

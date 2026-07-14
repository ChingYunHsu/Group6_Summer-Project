import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function ProfileGuestScreen() {
  const { t } = useTranslation();

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}

      <View style={styles.header}>
        {/* Not router.back() — this screen is reached via router.replace()
            from (tabs)/profile.tsx's guest redirect, so there's no
            reliable "previous screen" in history to return to. Map is
            the sensible default a browsing guest actually wants. */}
        <TouchableOpacity onPress={() => router.replace("/map")}>
          <Ionicons name="chevron-back" size={24} color={Colours.text} />
        </TouchableOpacity>

        <Text style={styles.logo}>ClearPath</Text>

        <Ionicons
          name="person-circle-outline"
          size={28}
          color={Colours.muted}
        />
      </View>

      {/* Locked Content */}

      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <Ionicons name="lock-closed" size={48} color={Colours.primary} />

          <View style={styles.userBadge}>
            <Ionicons name="person" size={14} color="#FFFFFF" />
          </View>
        </View>

        <Text style={styles.title}>{t("profileGuest.title")}</Text>

        <Text style={styles.description}>{t("profileGuest.description")}</Text>

        <TouchableOpacity
          style={styles.loginButton}
          onPress={() => router.push("/login")}
        >
          <Text style={styles.loginText}>
            {t("profileGuest.loginRegister")}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
    padding: 20,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },

  logo: {
    ...Typography.h2,
    color: Colours.primary,
    alignSelf: "center",
  },

  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },

  iconCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 30,
  },

  userBadge: {
    position: "absolute",
    bottom: 28,
    right: 28,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colours.primary,
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    ...Typography.h2,
    textAlign: "center",
    marginBottom: 16,
  },

  description: {
    ...Typography.body,
    color: Colours.muted,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
  },

  loginButton: {
    width: "100%",
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    justifyContent: "center",
    alignItems: "center",
  },

  loginText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
  },
});

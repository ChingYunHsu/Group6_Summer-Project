import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function AuthGatewayScreen() {
  const { t } = useTranslation();

  const handleLoginRegister = () => {
    router.push("/login");
  };

  const handleContinueAsGuest = () => {
    // Change to actual map route later
    router.push("/map");
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Icon */}

        <View style={styles.iconWrapper}>
          <View style={styles.iconCircle}>
            <Ionicons
              name="shield-checkmark-outline"
              size={72}
              color={Colours.primary}
            />
          </View>
        </View>

        {/* Heading */}

        <Text style={styles.title}>
  {t("authGateway.title")}
</Text>

        {/* Description */}

        <Text style={styles.subtitle}>
  {t("authGateway.subtitle")}
</Text>

        {/* Buttons */}

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={handleLoginRegister}
        >
          <Text style={styles.primaryButtonText}>
  {t("authGateway.loginRegister")}
</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={handleContinueAsGuest}
        >
          <Text style={styles.secondaryButtonText}>
  {t("authGateway.continueGuest")}
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
  },

  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },

  iconWrapper: {
    marginBottom: 36,
  },

  iconCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    ...Typography.h1,
    color: Colours.text,
    textAlign: "center",
    marginBottom: 16,
  },

  subtitle: {
    ...Typography.body,
    lineHeight: 26,
    color: Colours.muted,
    textAlign: "center",
    maxWidth: 320,
    marginBottom: 40,
  },

  primaryButton: {
    width: "100%",
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    marginBottom: 14,
  },

  primaryButtonText: {
    ...Typography.button,
    textAlign: "center",
    color: Colours.surface,
  },

  secondaryButton: {
    width: "100%",
    backgroundColor: Colours.surface,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 999,
    paddingVertical: 18,
  },

  secondaryButtonText: {
    ...Typography.button,
    textAlign: "center",
    color: Colours.primary,
  },
});
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Modal,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { login, register } from "../services/authService";

export default function LoginScreen() {
  const { t } = useTranslation();

  const [isRegisterMode, setIsRegisterMode] = useState(false);

  const [showPassword, setShowPassword] = useState(false);

  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");

  const [fullName, setFullName] = useState("");

  const [loading, setLoading] = useState(false);

  const [showRegistrationModal, setShowRegistrationModal] = useState(false);

  const [agreed, setAgreed] = useState(false);

  const handleSignIn = async () => {
    try {
      setLoading(true);

      await login(email, password);

      router.replace("/map");
    } catch (error: any) {
      console.error(error);

      Alert.alert(
        t("login.signInErrorTitle", { defaultValue: "Couldn't sign in" }),
        error?.message ??
          t("login.signInErrorMessage", {
            defaultValue: "Please check your details and try again.",
          }),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAccount = async () => {
    try {
      setLoading(true);

      const response = await register(fullName, email, password);

      if (response.finish_profile_prompt) {
        setShowRegistrationModal(true);
      } else {
        router.replace("/map");
      }
    } catch (error: any) {
      console.error(error);

      // The backend returns which fields failed (e.g. "password" for a
      // too-short password) — surfacing that is more actionable than the
      // generic "Validation failed." alone.
      const problemFields = [
        ...(error?.body?.missing_fields ?? []),
        ...(error?.body?.invalid_fields ?? []),
      ];

      const message = problemFields.length
        ? `${error.message} (${problemFields.join(", ")})`
        : (error?.message ??
          t("login.registerErrorMessage", {
            defaultValue: "Please check your details and try again.",
          }));

      Alert.alert(
        t("login.registerErrorTitle", {
          defaultValue: "Couldn't create account",
        }),
        message,
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFinishProfile = () => {
    setShowRegistrationModal(false);

    // replace() first, not push() — otherwise login.tsx stays underneath
    // in history, so backing out of medical-id.tsx would land on a stale
    // login form despite already being authenticated. replace() clears
    // it, then push() adds medical-id on top of the now-correct /map.
    router.replace("/map");
    router.push("/medical-id");
  };

  const handleSkipForNow = () => {
    setShowRegistrationModal(false);

    router.replace("/map");
  };

  return (
    <>
      <SafeAreaView style={styles.container}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="chevron-back" size={24} color={Colours.text} />
        </TouchableOpacity>

        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.card}>
            {!isRegisterMode ? (
              <>
                <Text style={styles.title}>{t("login.welcomeBack")}</Text>

                <Text style={styles.subtitle}>{t("login.signInSubtitle")}</Text>

                <Text style={styles.label}>{t("profile.email")}</Text>

                <TextInput
                  value={email}
                  onChangeText={setEmail}
                  placeholder={t("login.emailPlaceholder")}
                  placeholderTextColor={Colours.muted}
                  style={styles.input}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />

                <Text style={styles.label}>{t("login.password")}</Text>

                <View style={styles.passwordWrapper}>
                  <TextInput
                    value={password}
                    onChangeText={setPassword}
                    placeholder={t("login.passwordPlaceholder")}
                    placeholderTextColor={Colours.muted}
                    secureTextEntry={!showPassword}
                    style={styles.passwordInput}
                  />

                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                  >
                    <Ionicons
                      name={showPassword ? "eye-off-outline" : "eye-outline"}
                      size={22}
                      color={Colours.muted}
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  style={styles.primaryButton}
                  disabled={loading}
                  onPress={handleSignIn}
                >
                  <Text style={styles.primaryButtonText}>
                    {loading ? t("common.loading") : t("login.signIn")}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  testID="switch-to-register"
                  onPress={() => setIsRegisterMode(true)}
                >
                  <Text style={styles.switchText}>
                    {t("login.newHere", { defaultValue: "New here?" })}{" "}
                    <Text style={styles.linkText}>
                      {t("login.createAccount", {
                        defaultValue: "Create an account",
                      })}
                    </Text>
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.title}>{t("login.getStarted")}</Text>

                <Text style={styles.subtitle}>
                  {t("login.registerSubtitle")}
                </Text>

                <Text style={styles.label}>{t("profile.fullName")}</Text>

                <TextInput
                  value={fullName}
                  onChangeText={setFullName}
                  placeholder={t("login.fullNamePlaceholder")}
                  placeholderTextColor={Colours.muted}
                  style={styles.input}
                />

                <Text style={styles.label}>{t("profile.email")}</Text>

                <TextInput
                  value={email}
                  onChangeText={setEmail}
                  placeholder={t("login.emailPlaceholder")}
                  placeholderTextColor={Colours.muted}
                  style={styles.input}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />

                <Text style={styles.label}>{t("login.createPassword")}</Text>

                <View style={styles.passwordWrapper}>
                  <TextInput
                    value={password}
                    onChangeText={setPassword}
                    placeholder={t("login.passwordRequirements")}
                    placeholderTextColor={Colours.muted}
                    secureTextEntry={!showPassword}
                    style={styles.passwordInput}
                  />

                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                  >
                    <Ionicons
                      name={showPassword ? "eye-off-outline" : "eye-outline"}
                      size={22}
                      color={Colours.muted}
                    />
                  </TouchableOpacity>
                </View>

                <View style={styles.checkboxRow}>
                  <Switch
                    testID="terms-switch"
                    value={agreed}
                    onValueChange={setAgreed}
                    trackColor={{
                      false: Colours.border,
                      true: Colours.primary,
                    }}
                  />

                  <Text style={styles.checkboxText}>
                    {t("login.agreeTerms")}
                  </Text>
                </View>

                <TouchableOpacity
                  testID="create-account-button"
                  style={[
                    styles.primaryButton,
                    (!agreed || loading) && styles.disabledButton,
                  ]}
                  disabled={!agreed || loading}
                  onPress={handleCreateAccount}
                >
                  <Text style={styles.primaryButtonText}>
                    {loading ? t("common.loading") : t("login.createAccount")}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  testID="switch-to-signin"
                  onPress={() => setIsRegisterMode(false)}
                >
                  <Text style={styles.switchText}>
                    {t("login.alreadyHaveAccount")}{" "}
                    <Text style={styles.linkText}>{t("login.signIn")}</Text>
                  </Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          <View style={styles.footer}>
            <Ionicons name="lock-closed" size={14} color={Colours.muted} />

            <Text style={styles.footerText}>{t("login.encryption")}</Text>
          </View>
        </ScrollView>
      </SafeAreaView>

      <Modal visible={showRegistrationModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.sheetHandle} />

            <Text style={styles.modalTitle}>
              {t("login.finishProfileTitle")}
            </Text>

            <Text style={styles.modalDescription}>
              {t("login.finishProfileDescription")}
            </Text>

            <TouchableOpacity
              testID="finish-profile-button"
              style={styles.modalPrimaryButton}
              onPress={handleFinishProfile}
            >
              <Text style={styles.primaryButtonText}>
                {t("login.finishProfile")}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              testID="skip-for-now-button"
              style={styles.modalSecondaryButton}
              onPress={handleSkipForNow}
            >
              <Text style={styles.secondaryButtonText}>
                {t("login.skipForNow")}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  backButton: {
    position: "absolute",
    top: 16,
    left: 16,
    zIndex: 10,
    padding: 8,
  },

  content: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 20,
  },

  card: {
    backgroundColor: Colours.surface,
    borderRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  title: {
    ...Typography.h1,
    color: Colours.text,
    marginBottom: 8,
  },

  subtitle: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginBottom: 28,
  },

  label: {
    ...Typography.bodySmall,
    color: Colours.text,
    fontWeight: "600",
    marginBottom: 8,
  },

  input: {
    height: 56,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 14,
    paddingHorizontal: 16,
    backgroundColor: Colours.surface,
    color: Colours.text,
    marginBottom: 18,
  },

  passwordWrapper: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 14,
    paddingHorizontal: 16,
    height: 56,
    marginBottom: 24,
    backgroundColor: Colours.surface,
  },

  passwordInput: {
    flex: 1,
    color: Colours.text,
  },

  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 24,
  },

  checkboxText: {
    flex: 1,
    marginLeft: 10,
    color: Colours.muted,
  },

  primaryButton: {
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    marginBottom: 16,
  },

  primaryButtonText: {
    ...Typography.button,
    color: Colours.surface,
    textAlign: "center",
  },

  disabledButton: {
    opacity: 0.4,
  },

  secondaryButton: {
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 999,
    paddingVertical: 18,
    marginTop: 12,
    backgroundColor: Colours.surface,
  },

  secondaryButtonText: {
    ...Typography.button,
    color: Colours.text,
    textAlign: "center",
  },

  switchText: {
    textAlign: "center",
    color: Colours.muted,
  },

  linkText: {
    color: Colours.primary,
    fontWeight: "700",
  },

  footer: {
    marginTop: 24,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  footerText: {
    ...Typography.caption,
    marginLeft: 6,
    color: Colours.muted,
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.3)",
    justifyContent: "flex-end",
  },

  modalCard: {
    backgroundColor: Colours.surface,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 28,
    paddingTop: 20,
    paddingBottom: 40,
  },

  modalTitle: {
    ...Typography.h3,
    color: Colours.text,
    textAlign: "center",
    alignSelf: "center",
    marginBottom: 12,
    maxWidth: 320,
  },

  modalDescription: {
    ...Typography.bodySmall,
    color: Colours.muted,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 24,
  },

  modalPrimaryButton: {
    width: "100%",
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    marginBottom: 12,
    alignSelf: "center",
  },

  modalSecondaryButton: {
    width: "100%",
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 999,
    paddingVertical: 18,
    backgroundColor: Colours.surface,
    alignSelf: "center",
  },

  sheetHandle: {
    width: 40,
    height: 5,
    borderRadius: 999,
    backgroundColor: Colours.border,
    alignSelf: "center",
    marginBottom: 20,
  },
});

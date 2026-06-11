import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import {
    Modal,
    SafeAreaView,
    ScrollView,
    StyleSheet,
    Switch,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function LoginScreen() {
  const [isRegisterMode, setIsRegisterMode] =
    useState(false);

  const [showPassword, setShowPassword] =
    useState(false);

  const [
    showRegistrationModal,
    setShowRegistrationModal,
  ] = useState(false);

  const [agreed, setAgreed] =
    useState(false);

  const handleSignIn = () => {
    router.push("/map");
  };

  const handleCreateAccount = () => {
    setShowRegistrationModal(true);
  };

  const handleFinishProfile = () => {
    setShowRegistrationModal(false);

    // Future route
    router.push("/profile");
  };

  const handleSkipForNow = () => {
    setShowRegistrationModal(false);

    // Future route
    router.push("/map");
  };

  return (
    <>
      <SafeAreaView style={styles.container}>
        <ScrollView
          contentContainerStyle={
            styles.content
          }
          showsVerticalScrollIndicator={
            false
          }
        >
          <View style={styles.card}>
            {!isRegisterMode ? (
              <>
                <Text style={styles.title}>
                  Welcome back
                </Text>

                <Text
                  style={styles.subtitle}
                >
                  Access your international
                  health records.
                </Text>

                <Text
                  style={styles.label}
                >
                  Email Address
                </Text>

                <TextInput
                  placeholder="name@company.com"
                  placeholderTextColor={
                    Colours.muted
                  }
                  style={styles.input}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />

                <Text
                  style={styles.label}
                >
                  Password
                </Text>

                <View
                  style={
                    styles.passwordWrapper
                  }
                >
                  <TextInput
                    placeholder="••••••••"
                    placeholderTextColor={
                      Colours.muted
                    }
                    secureTextEntry={
                      !showPassword
                    }
                    style={
                      styles.passwordInput
                    }
                  />

                  <TouchableOpacity
                    onPress={() =>
                      setShowPassword(
                        !showPassword
                      )
                    }
                  >
                    <Ionicons
                      name={
                        showPassword
                          ? "eye-off-outline"
                          : "eye-outline"
                      }
                      size={22}
                      color={Colours.muted}
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  style={
                    styles.primaryButton
                  }
                  onPress={
                    handleSignIn
                  }
                >
                  <Text
                    style={
                      styles.primaryButtonText
                    }
                  >
                    Sign In
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={() =>
                    setIsRegisterMode(
                      true
                    )
                  }
                >
                  <Text
                    style={
                      styles.switchText
                    }
                  >
                    New here?{" "}
                    <Text
                      style={
                        styles.linkText
                      }
                    >
                      Create an account
                    </Text>
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.title}>
                  Get started
                </Text>

                <Text
                  style={styles.subtitle}
                >
                  Reliable care for
                  international travellers.
                </Text>

                <Text
                  style={styles.label}
                >
                  Full Name
                </Text>

                <TextInput
                  placeholder="John Doe"
                  placeholderTextColor={
                    Colours.muted
                  }
                  style={styles.input}
                />

                <Text
                  style={styles.label}
                >
                  Email Address
                </Text>

                <TextInput
                  placeholder="name@company.com"
                  placeholderTextColor={
                    Colours.muted
                  }
                  style={styles.input}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />

                <Text
                  style={styles.label}
                >
                  Create Password
                </Text>

                <View
                  style={
                    styles.passwordWrapper
                  }
                >
                  <TextInput
                    placeholder="Minimum 8 characters"
                    placeholderTextColor={
                      Colours.muted
                    }
                    secureTextEntry={
                      !showPassword
                    }
                    style={
                      styles.passwordInput
                    }
                  />

                  <TouchableOpacity
                    onPress={() =>
                      setShowPassword(
                        !showPassword
                      )
                    }
                  >
                    <Ionicons
                      name={
                        showPassword
                          ? "eye-off-outline"
                          : "eye-outline"
                      }
                      size={22}
                      color={Colours.muted}
                    />
                  </TouchableOpacity>
                </View>

                <View
                  style={
                    styles.checkboxRow
                  }
                >
                  <Switch
                    value={agreed}
                    onValueChange={
                      setAgreed
                    }
                    trackColor={{
                      false:
                        Colours.border,
                      true:
                        Colours.primary,
                    }}
                  />

                  <Text
                    style={
                      styles.checkboxText
                    }
                  >
                    I agree to the Terms
                    of Service and Privacy
                    Policy
                  </Text>
                </View>

                <TouchableOpacity
                  style={[
                    styles.primaryButton,
                    !agreed &&
                      styles.disabledButton,
                  ]}
                  disabled={!agreed}
                  onPress={
                    handleCreateAccount
                  }
                >
                  <Text
                    style={
                      styles.primaryButtonText
                    }
                  >
                    Create Account
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={() =>
                    setIsRegisterMode(
                      false
                    )
                  }
                >
                  <Text
                    style={
                      styles.switchText
                    }
                  >
                    Already have an
                    account?{" "}
                    <Text
                      style={
                        styles.linkText
                      }
                    >
                      Sign In
                    </Text>
                  </Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          <View style={styles.footer}>
            <Ionicons
              name="lock-closed"
              size={14}
              color={Colours.muted}
            />

            <Text
              style={styles.footerText}
            >
              256-bit HIPAA compliant
              encryption
            </Text>
          </View>
        </ScrollView>
      </SafeAreaView>

      <Modal
        visible={showRegistrationModal}
        transparent
        animationType="fade"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Ionicons
              name="checkmark-circle"
              size={64}
              color={Colours.success}
            />

            <Text
              style={styles.modalTitle}
            >
              Registration Successful!
            </Text>

            <Text
              style={
                styles.modalDescription
              }
            >
              Would you like to finish
              setting up your Medical
              Profile and ID now?
            </Text>

            <TouchableOpacity
              style={
                styles.modalPrimaryButton
              }
              onPress={
                handleFinishProfile
              }
            >
              <Text
                style={
                  styles.primaryButtonText
                }
              >
                Finish Profile & ID
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={
                styles.modalSecondaryButton
              }
              onPress={handleSkipForNow}
            >
              <Text
                style={
                  styles.secondaryButtonText
                }
              >
                Skip For Now
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
    backgroundColor:
      "rgba(0,0,0,0.5)",
    justifyContent: "center",
    padding: 24,
  },

  modalCard: {
    backgroundColor: Colours.surface,
    borderRadius: 24,
    padding: 24,
    alignItems: "center",
  },

  modalTitle: {
    ...Typography.h3,
    color: Colours.text,
    marginTop: 16,
    marginBottom: 12,
  },

  modalDescription: {
    ...Typography.bodySmall,
    color: Colours.muted,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 24,
  },

modalPrimaryButton: {
  width: "90%",
  backgroundColor: Colours.primary,
  borderRadius: 999,
  paddingVertical: 18,
  marginBottom: 12,
},

modalSecondaryButton: {
  width: "90%",
  borderWidth: 1,
  borderColor: Colours.border,
  borderRadius: 999,
  paddingVertical: 18,
  backgroundColor: Colours.surface,
},
});
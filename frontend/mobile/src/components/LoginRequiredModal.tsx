import { useRouter } from "expo-router";
import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { useTranslation } from "react-i18next";

type Props = {
  visible: boolean;
  onClose: () => void;
};

// Shown whenever a logged-out user tries to do something that requires
// an account (favouriting, reporting, confirming a report) — offers to
// send them to login/register, or just cancel.
export default function LoginRequiredModal({ visible, onClose }: Props) {
  const router = useRouter();

  const { t } = useTranslation();

  // Closes this modal first, then navigates after a short delay so the
  // close animation isn't cut off by the screen transition.
  const handleLogin = () => {
    onClose();

    // slight delay so modal closes smoothly
    setTimeout(() => {
      router.push("/login");
    }, 200);
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>{t("login.loginRequiredTitle")}</Text>

          <Text style={styles.body}>{t("login.loginRequiredBody")}</Text>

          <TouchableOpacity style={styles.primaryButton} onPress={handleLogin}>
            <Text style={styles.primaryText}>{t("login.logInSignUp")}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryButton} onPress={onClose}>
            <Text style={styles.secondaryText}>{t("common.cancel")}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },

  card: {
    width: "100%",
    backgroundColor: "white",
    borderRadius: 24,
    padding: 24,
  },

  title: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 12,
    textAlign: "center",
  },

  body: {
    fontSize: 16,
    lineHeight: 24,
    textAlign: "center",
    color: "#555",
    marginBottom: 24,
  },

  primaryButton: {
    backgroundColor: "#2563EB",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
    marginBottom: 12,
  },

  primaryText: {
    color: "white",
    fontWeight: "700",
    fontSize: 16,
  },

  secondaryButton: {
    paddingVertical: 16,
    alignItems: "center",
  },

  secondaryText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#666",
  },
});

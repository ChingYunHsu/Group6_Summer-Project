import { useRouter } from "expo-router";
import {
    Modal,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

type Props = {
  visible: boolean;
  onClose: () => void;
};

export default function LoginRequiredModal({
  visible,
  onClose,
}: Props) {
  const router = useRouter();

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

          <Text style={styles.title}>
            Login Required
          </Text>

          <Text style={styles.body}>
            To help keep ClearPath data accurate and prevent spam,
            you must be logged in to submit or verify community
            reports.
          </Text>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleLogin}
          >
            <Text style={styles.primaryText}>
              Log In / Sign Up
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={onClose}
          >
            <Text style={styles.secondaryText}>
              Cancel
            </Text>
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
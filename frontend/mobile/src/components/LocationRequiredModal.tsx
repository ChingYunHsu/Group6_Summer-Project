import { useTranslation } from "react-i18next";
import {
  Linking,
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

export default function LocationRequiredModal({ visible, onClose }: Props) {
  const { t } = useTranslation();

  const handleSettings = async () => {
    onClose();

    try {
      await Linking.openSettings();
    } catch (e) {
      console.warn(t("location.settingsError"));
    }
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
            {t("location.servicesRequiredTitle")}
          </Text>

          <Text style={styles.body}>{t("location.servicesRequiredBody")}</Text>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleSettings}
          >
            <Text style={styles.primaryText}>
              {t("location.systemSettings")}
            </Text>
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

    backgroundColor: "#FFFFFF",

    borderRadius: 24,

    padding: 24,
  },

  title: {
    fontSize: 22,

    fontWeight: "700",

    textAlign: "center",

    marginBottom: 12,
  },

  body: {
    textAlign: "center",

    fontSize: 16,

    color: "#555",

    lineHeight: 24,

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
    color: "#FFF",

    fontWeight: "700",

    fontSize: 16,
  },

  secondaryButton: {
    alignItems: "center",

    paddingVertical: 16,
  },

  secondaryText: {
    color: "#666",

    fontWeight: "600",

    fontSize: 16,
  },
});

import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { mockMedicalId } from "../data/mockMedicalId";
import { mockProfile } from "../data/mockProfile";

export default function SOSScreen() {
  const [countdown, setCountdown] = useState(5);

  const { t } = useTranslation();

  useEffect(() => {
    if (countdown === 0) {
      handleCallEmergency();
      return;
    }

    const timer = setTimeout(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [countdown]);

  const handleCallEmergency = async () => {
    const phoneNumber = "911";
    const url = `tel:${phoneNumber}`;
    // Replace with region-specific emergency number if the app expands outside the US

    const supported = await Linking.canOpenURL(url);

    if (!supported) {
      Alert.alert(t("sos.callErrorTitle"), t("sos.callErrorMessage"));
      return;
    }

    await Linking.openURL(url);
  };

  const handleCancel = () => {
    router.back();
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Close */}

        <TouchableOpacity style={styles.closeButton} onPress={handleCancel}>
          <Ionicons name="close" size={28} color="#FFFFFF" />
        </TouchableOpacity>

        {/* Hero */}

        <View style={styles.hero}>
          <Ionicons name="warning" size={64} color="#FFFFFF" />

          <Text style={styles.sosTitle}>{t("sos.title")}</Text>

          <Text style={styles.timer}>
            {t("sos.countdown", { seconds: countdown })}
          </Text>

          <Text style={styles.subtitle}>{t("sos.subtitle")}</Text>
        </View>

        {/* Location TODO: WIRE TO LIVE LOCATION */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{t("sos.locationTitle")}</Text>

          <Text style={styles.cardText}>245 W 46th St, New York, NY 10036</Text>

          <Text style={styles.cardSubtext}>{t("sos.locationDescription")}</Text>
        </View>

        {/* Medical ID */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{t("sos.medicalIdTitle")}</Text>

          <InfoRow label={t("sos.name")} value={mockProfile.full_name} />

          <InfoRow
            label={t("sos.bloodType")}
            value={mockMedicalId.blood_type}
          />

          <InfoRow
            label={t("sos.conditions")}
            value={mockMedicalId.conditions?.join(", ") ?? t("sos.none")}
          />

          <InfoRow
            label={t("sos.allergies")}
            value={mockMedicalId.allergies?.join(", ") ?? t("sos.none")}
          />

          <InfoRow label={t("sos.phone")} value={mockProfile.phone} />
        </View>

        {/* Emergency Notice */}

        <View style={styles.notice}>
          <Ionicons name="information-circle" size={20} color="#FFFFFF" />

          <Text style={styles.noticeText}>{t("sos.notice")}</Text>
        </View>

        {/* Cancel */}

        <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
          <Text style={styles.cancelText}>{t("sos.cancel")}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

type InfoRowProps = {
  label: string;
  value: string | null;
};

function InfoRow({ label, value }: InfoRowProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>

      <Text style={styles.infoValue}>{value ?? t("sos.notProvided")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#C62828",
  },

  closeButton: {
    position: "absolute",
    top: 12,
    left: 12,
    zIndex: 10,
  },

  hero: {
    alignItems: "center",
    marginTop: 20,
    marginBottom: 30,
  },

  sosTitle: {
    fontSize: 34,
    fontWeight: "800",
    color: "#FFFFFF",
    marginTop: 12,
    textAlign: "center",
  },

  timer: {
    fontSize: 42,
    fontWeight: "800",
    color: "#FFFFFF",
    marginTop: 10,
  },

  subtitle: {
    color: "#FFFFFF",
    textAlign: "center",
    marginTop: 12,
    opacity: 0.9,
    fontSize: 16,
    lineHeight: 22,
  },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
  },

  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 12,
  },

  cardText: {
    color: Colours.text,
    marginBottom: 6,
  },

  cardSubtext: {
    color: Colours.muted,
    fontSize: 12,
    lineHeight: 18,
  },

  infoRow: {
    marginBottom: 12,
  },

  infoLabel: {
    fontSize: 12,
    color: Colours.muted,
    marginBottom: 2,
  },

  infoValue: {
    color: Colours.text,
    fontSize: 15,
  },

  notice: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
    marginBottom: 20,
  },

  noticeText: {
    color: "#FFFFFF",
    marginLeft: 10,
    flex: 1,
    lineHeight: 20,
  },

  cancelButton: {
    backgroundColor: "#FFFFFF",
    borderRadius: 999,
    paddingVertical: 18,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 12,
  },

  cancelText: {
    color: "#C62828",
    fontWeight: "800",
    fontSize: 16,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 32,
  },
});

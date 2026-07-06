import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
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
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (value: number) => {
    const mins = Math.floor(value / 60)
      .toString()
      .padStart(2, "0");

    const secs = (value % 60)
      .toString()
      .padStart(2, "0");

    return `${mins}:${secs}`;
  };

  const handleCancel = () => {
    router.back();
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}

      <TouchableOpacity
        style={styles.closeButton}
        onPress={handleCancel}
      >
        <Ionicons
          name="close"
          size={28}
          color="#FFFFFF"
        />
      </TouchableOpacity>

      {/* SOS Status */}

      <View style={styles.hero}>
        <Ionicons
          name="warning"
          size={64}
          color="#FFFFFF"
        />

        <Text style={styles.sosTitle}>
          SOS ACTIVE
        </Text>

        <Text style={styles.timer}>
          {formatTime(seconds)}
        </Text>

        <Text style={styles.subtitle}>
          Emergency assistance has been
          requested.
        </Text>
      </View>

      {/* Location */}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>
          Current Location
        </Text>

        <Text style={styles.cardText}>
          245 W 46th St, New York, NY 10036
        </Text>

        <Text style={styles.cardSubtext}>
          GPS coordinates will be provided
          to emergency responders.
        </Text>
      </View>

      {/* Medical ID */}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>
          Medical ID Summary
        </Text>

        <InfoRow
          label="Name"
          value={mockProfile.full_name}
        />

        <InfoRow
          label="Blood Type"
          value={mockMedicalId.blood_type}
        />

        <InfoRow
          label="Conditions"
          value={mockMedicalId.conditions.join(
            ", "
          )}
        />

        <InfoRow
          label="Allergies"
          value={mockMedicalId.allergies.join(
            ", "
          )}
        />

        <InfoRow
          label="Phone"
          value={mockProfile.phone}
        />
      </View>

      {/* Emergency Notice */}

      <View style={styles.notice}>
        <Ionicons
          name="shield-checkmark"
          size={20}
          color="#FFFFFF"
        />

        <Text style={styles.noticeText}>
          Emergency profile information is
          ready to share with responders.
        </Text>
      </View>

      {/* Cancel */}

      <TouchableOpacity
        style={styles.cancelButton}
        onPress={handleCancel}
      >
        <Text style={styles.cancelText}>
          HOLD 3S TO CANCEL
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

type InfoRowProps = {
  label: string;
  value: string;
};

function InfoRow({
  label,
  value,
}: InfoRowProps) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>
        {label}
      </Text>

      <Text style={styles.infoValue}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#C62828",
    padding: 20,
  },

  closeButton: {
    position: "absolute",
    top: 12,
    left: 12,
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
  },

  cancelButton: {
    backgroundColor: "#FFFFFF",
    borderRadius: 999,
    paddingVertical: 18,
    justifyContent: "center",
    alignItems: "center",
    marginTop: "auto",
  },

  cancelText: {
    color: "#C62828",
    fontWeight: "800",
    fontSize: 16,
  },
});

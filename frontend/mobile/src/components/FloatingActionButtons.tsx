import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Ionicons } from "@expo/vector-icons";

interface Props {
  onSOSPress: () => void;
  onReportPress: () => void;
}

export default function FloatingActionButtons({
  onSOSPress,
  onReportPress,
}: Props) {
  return (
    <View style={styles.container}>
      <TouchableOpacity
        testID="floating-report-button"
        style={styles.reportButton}
        activeOpacity={0.85}
        onPress={onReportPress}
      >
        <Ionicons name="warning" size={24} color="#111827" />
      </TouchableOpacity>

      <TouchableOpacity
        testID="floating-sos-button"
        style={styles.sosButton}
        activeOpacity={0.9}
        onPress={onSOSPress}
      >
        <Text style={styles.sosText}>SOS</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",

    right: 20,

    bottom: 36,

    alignItems: "center",
  },

  reportButton: {
    width: 58,

    height: 58,

    borderRadius: 29,

    backgroundColor: "#FACC15",

    justifyContent: "center",

    alignItems: "center",

    marginBottom: 14,

    shadowColor: "#000",

    shadowOpacity: 0.15,

    shadowRadius: 6,

    shadowOffset: {
      width: 0,

      height: 2,
    },

    elevation: 5,
  },

  sosButton: {
    width: 76,

    height: 76,

    borderRadius: 38,

    backgroundColor: "#DC2626",

    justifyContent: "center",

    alignItems: "center",

    shadowColor: "#000",

    shadowOpacity: 0.25,

    shadowRadius: 8,

    shadowOffset: {
      width: 0,

      height: 3,
    },

    elevation: 8,
  },

  sosText: {
    color: "#FFFFFF",

    fontWeight: "800",

    fontSize: 18,

    letterSpacing: 0.5,
  },
});

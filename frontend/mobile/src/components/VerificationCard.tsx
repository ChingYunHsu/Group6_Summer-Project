import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

interface VerificationCardProps {
  title?: string;
  reportedAt: string;
  confirmations: number;
  onConfirm: () => void;
  onResolve: () => void;
}

export default function VerificationCard({
  title = "Is this still an issue?",
  reportedAt,
  confirmations,
  onConfirm,
  onResolve,
}: VerificationCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>

      <Text style={styles.reported}>Reported {reportedAt}</Text>

      <Text style={styles.confirmations}>
        ({confirmations} user{confirmations === 1 ? "" : "s"} confirmed)
      </Text>

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.confirmButton} onPress={onConfirm}>
          <Text style={styles.confirmText}>Confirm</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.resolveButton} onPress={onResolve}>
          <Text style={styles.resolveText}>Resolve</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: 16,
    padding: 16,
    borderRadius: 14,
    backgroundColor: "#FEE2E2",
    borderWidth: 1,
    borderColor: "#FCA5A5",
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },

  title: {
    marginLeft: 8,
    fontSize: 16,
    fontWeight: "700",
    color: "#92400E",
  },

  reported: {
    color: "#6B7280",
    marginBottom: 6,
  },

  confirmations: {
    fontWeight: "600",
    color: "#166534",
    marginBottom: 14,
  },

  buttonRow: {
    flexDirection: "row",
    marginTop: 16,
  },

  confirmButton: {
    flex: 1,
    backgroundColor: "#DC2626",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    marginRight: 6,
  },

  resolveButton: {
    flex: 1,
    backgroundColor: "#DBEAFE",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    marginLeft: 6,
  },

  confirmText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },

  resolveText: {
    color: "#1D4ED8",
    fontWeight: "700",
  },
});

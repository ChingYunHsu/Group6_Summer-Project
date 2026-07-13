import {
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

interface Props {
  issue: string;
  reportedAt: string;
  confirmations: number;
  onConfirm: () => void;
  onResolve: () => void;
}

export default function ReportCallout({
  issue,
  reportedAt,
  confirmations,
  onConfirm,
  onResolve,
}: Props) {
  return (
    <View style={styles.container}>

      <Text style={styles.issue}>
        {issue}
      </Text>

      <Text style={styles.time}>
        Reported {reportedAt}
      </Text>

      <Text style={styles.confirmations}>
        {confirmations} users confirmed
      </Text>

      <View style={styles.buttonRow}>

        <TouchableOpacity
          style={styles.confirmButton}
          onPress={onConfirm}
        >
          <Text style={styles.confirmText}>
            Confirm
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.resolveButton}
          onPress={onResolve}
        >
          <Text style={styles.resolveText}>
            Resolve
          </Text>
        </TouchableOpacity>

      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    width: 240,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 14,
  },

  issue: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 6,
  },

  time: {
    fontSize: 13,
    color: "#6B7280",
    marginBottom: 4,
  },

  confirmations: {
    fontSize: 13,
    color: "#2563EB",
    fontWeight: "600",
    marginBottom: 14,
  },

  buttonRow: {
    flexDirection: "row",
  },

  confirmButton: {
    flex: 1,
    backgroundColor: "#2563EB",
    borderRadius: 8,
    alignItems: "center",
    paddingVertical: 10,
    marginRight: 5,
  },

  resolveButton: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    alignItems: "center",
    paddingVertical: 10,
    marginLeft: 5,
  },

  confirmText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },

  resolveText: {
    color: "#374151",
    fontWeight: "700",
  },

});
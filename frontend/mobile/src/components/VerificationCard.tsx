import { useTranslation } from "react-i18next";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

interface VerificationCardProps {
  title?: string;
  reportedAt: string;
  confirmations: number;
  onConfirm: () => void;
  onResolve: () => void;
}

export default function VerificationCard({
  title,
  reportedAt,
  confirmations,
  onConfirm,
  onResolve,
}: VerificationCardProps) {
  const { t } = useTranslation();

  const resolvedTitle =
    title ??
    t("verification.defaultTitle", {
      defaultValue: "Is this still an issue?",
    });

  const confirmationsText =
    confirmations === 1
      ? t("verification.confirmationSingular", {
          count: confirmations,
          defaultValue: "({{count}} user confirmed)",
        })
      : t("verification.confirmationPlural", {
          count: confirmations,
          defaultValue: "({{count}} users confirmed)",
        });

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{resolvedTitle}</Text>

      <Text style={styles.reported}>
        {t("verification.reportedAt", {
          time: reportedAt,
          defaultValue: "Reported {{time}}",
        })}
      </Text>

      <Text style={styles.confirmations}>{confirmationsText}</Text>

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.confirmButton} onPress={onConfirm}>
          <Text style={styles.confirmText}>
            {t("verification.confirm", { defaultValue: "Confirm" })}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.resolveButton} onPress={onResolve}>
          <Text style={styles.resolveText}>
            {t("verification.resolve", { defaultValue: "Resolve" })}
          </Text>
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

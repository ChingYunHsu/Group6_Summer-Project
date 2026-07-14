import { Ionicons } from "@expo/vector-icons";
import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { Report } from "../types/venue";
import { formatReportedTime } from "./ReportMarker";
import VerificationCard from "./VerificationCard";

interface Props {
  visible: boolean;
  report: Report | null;
  onClose: () => void;
  onConfirm: (reportId: string) => void;
  onResolve: (reportId: string) => void;
}

export default function ReportBottomSheet({
  visible,
  report,
  onClose,
  onConfirm,
  onResolve,
}: Props) {
  if (!report) return null;

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>
                {report.issue_type_label ?? report.issue_type}
              </Text>
            </View>

            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={26} color={Colours.text} />
            </TouchableOpacity>
          </View>

          <VerificationCard
            reportedAt={formatReportedTime(report.created_at)}
            confirmations={report.confirmations.count}
            onConfirm={() => onConfirm(report.report_id)}
            onResolve={() => onResolve(report.report_id)}
          />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.25)",
  },

  sheet: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
  },

  handle: {
    alignSelf: "center",
    width: 48,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#D1D5DB",
    marginBottom: 20,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
  },

  title: {
    ...Typography.h2,
    color: Colours.text,
  },
});

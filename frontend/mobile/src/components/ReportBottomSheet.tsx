import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
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

const ISSUE_TYPE_TRANSLATION_KEYS: Record<string, string> = {
  large_crowd: "reportModal.issueTypes.largeCrowd",
  entrance_closed: "reportModal.issueTypes.entranceClosed",
  elevator_broken: "reportModal.issueTypes.elevatorBroken",
  wheelchair_lift_broken: "reportModal.issueTypes.wheelchairLiftBroken",
  toilet_out_of_order: "reportModal.issueTypes.toiletOutOfOrder",
  protest_or_blockage: "reportModal.issueTypes.protestOrBlockage",
};

export default function ReportBottomSheet({
  visible,
  report,
  onClose,
  onConfirm,
  onResolve,
}: Props) {
  const { t } = useTranslation();

  if (!report) return null;

  const title = t(
    ISSUE_TYPE_TRANSLATION_KEYS[report.issue_type] ?? report.issue_type,
    { defaultValue: report.issue_type_label ?? report.issue_type },
  );

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{title}</Text>
            </View>

            <TouchableOpacity accessibilityLabel="Close" onPress={onClose}>
              <Ionicons name="close" size={26} color={Colours.text} />
            </TouchableOpacity>
          </View>

          <VerificationCard
            reportedAt={formatReportedTime(report.created_at, t)}
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

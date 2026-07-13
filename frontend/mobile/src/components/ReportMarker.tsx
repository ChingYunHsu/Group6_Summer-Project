import { Ionicons } from "@expo/vector-icons";
import { StyleSheet } from "react-native";
import { Callout, Marker } from "react-native-maps";

import { Report } from "../types/venue";
import ReportCallout from "./ReportCallout";

interface Props {
  report: Report;
  onConfirm?: (reportId: string) => void;
  onResolve?: (reportId: string) => void;
}

export function formatReportedTime(createdAt: string) {
  const minutes = Math.floor(
    (Date.now() - new Date(createdAt).getTime()) / 60000,
  );

  if (minutes < 60) {
    return `${minutes} min ago`;
  }

  const hours = Math.floor(minutes / 60);
  return `${hours} hr${hours === 1 ? "" : "s"} ago`;
}

export default function ReportMarker({ report, onConfirm, onResolve }: Props) {
  if (report.status !== "active") {
    return null;
  }

  return (
    <Marker
      coordinate={{
        latitude: report.latitude,
        longitude: report.longitude,
      }}
    >
      <Ionicons name="warning" size={36} color="#FACC15" style={styles.icon} />

      <Callout tooltip>
        <ReportCallout
          issue={report.issue_type_label ?? report.issue_type}
          reportedAt={formatReportedTime(report.created_at)}
          confirmations={report.confirmations.count}
          onConfirm={() => onConfirm?.(report.report_id)}
          onResolve={() => onResolve?.(report.report_id)}
        />
      </Callout>
    </Marker>
  );
}

const styles = StyleSheet.create({
  marker: {
    width: 36,
    height: 36,
    borderRadius: 18,

    justifyContent: "center",
    alignItems: "center",

    backgroundColor: "#FACC15",

    borderWidth: 3,
    borderColor: "#FFFFFF",

    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 5,

    shadowOffset: {
      width: 0,
      height: 2,
    },

    elevation: 5,
  },

  icon: {
    textShadowColor: "#FFFFFF",
    textShadowRadius: 3,
    textShadowOffset: {
      width: 0,
      height: 0,
    },
  },
});

import { Ionicons } from "@expo/vector-icons";
import { TFunction } from "i18next";
import { StyleSheet } from "react-native";
import { Marker } from "react-native-maps";

import { Report } from "../types/venue";

interface Props {
  report: Report;
  onPress: (report: Report) => void;
}

export function formatReportedTime(createdAt: string, t: TFunction): string {
  const minutes = Math.floor(
    (Date.now() - new Date(createdAt).getTime()) / 60000,
  );

  if (minutes < 60) {
    return t("time.minutesAgo", {
      defaultValue: "{{count}} min ago",
      count: minutes,
    });
  }

  const hours = Math.floor(minutes / 60);

  return t("time.hoursAgo", {
    defaultValue: "{{count}} hr ago",
    defaultValue_plural: "{{count}} hrs ago",
    count: hours,
  });
}

export default function ReportMarker({ report, onPress }: Props) {
  if (report.status !== "active") {
    return null;
  }

  return (
    <Marker
      accessibilityLabel={`Report: ${report.issue_type_label ?? report.issue_type}`}
      coordinate={{
        latitude: Number(report.latitude),
        longitude: Number(report.longitude),
      }}
      onPress={() => onPress(report)}
    >
      <Ionicons name="warning" size={36} color="#FACC15" style={styles.icon} />
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

import { Ionicons } from "@expo/vector-icons";
import { StyleSheet } from "react-native";
import { Marker } from "react-native-maps";

import { Report } from "../types/venue";

interface Props {
  report: Report;
  onPress: (report: Report) => void;
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

export default function ReportMarker({ report, onPress }: Props) {
  if (report.status !== "active") {
    return null;
  }

  return (
    <Marker
      coordinate={{
        // Same fix as VenueMarker.tsx — user_reports.latitude/longitude
        // are also MySQL DECIMAL columns, same string-serialization issue.
        latitude: Number(report.latitude),
        longitude: Number(report.longitude),
      }}
      onPress={() => onPress(report)}
    >
      <Ionicons name="warning" size={36} color="#FACC15" style={styles.icon} />

      {/* No Callout/CalloutSubview here anymore — react-native-maps'
          Callout renders as a flattened native snapshot on iOS with touch
          regions overlaid in a separate pass, and the two can fall out of
          sync (confirmed: broken/collapsed rendering for the Confirm/
          Resolve buttons even after several styling attempts). Tapping
          the marker now opens a real Modal-based bottom sheet instead —
          see ReportBottomSheet.tsx, which reuses the same reliable
          Modal pattern VenueBottomSheet already uses successfully. */}
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


import {
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { Venue } from "../types/venue";
import VerificationCard from "./VerificationCard";

interface Props {
  visible: boolean;
  venue: Venue | null;
  autoCurrentTime: boolean;
  onClose: () => void;
}

export default function VenueBottomSheet({
  visible,
  venue,
  autoCurrentTime,
  onClose,
}: Props) {
  if (!venue) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
    >
      <View style={styles.overlay}>

        <View style={styles.sheet}>

          <View style={styles.handle} />

          <View style={styles.header}>

            <View style={{ flex: 1 }}>

              <Text style={styles.title}>
                {venue.name}
              </Text>

              <Text style={styles.address}>
                {venue.address}
              </Text>

            </View>

            <TouchableOpacity
              onPress={onClose}
            >
              <Ionicons
                name="close"
                size={26}
                color={Colours.text}
              />
            </TouchableOpacity>

          </View>
{venue.active_warning && (
  <> 
    <View style={styles.alertStrip}>
      <Ionicons
        name="warning"
        size={18}
        color="#FFFFFF"
      />

      <Text style={styles.alertText}>
        Accessibility issue recently reported
      </Text>
    </View>

    <VerificationCard
      reportedAt="18 minutes ago"
      confirmations={3}
      onConfirm={() => console.log("Confirm issue")}
      onResolve={() => console.log("Resolve issue")}
    /> 
    
    <Text style={styles.sectionTitle}>
    Services
</Text>

<View style={styles.badgeRow}>
    {venue.supported_services.map(service => (
        <View
            key={service}
            style={styles.badge}
        >
            <Text style={styles.badgeText}>
                {service}
            </Text>
        </View>
    ))}
</View>

{autoCurrentTime ? (
  <>
    <Text style={styles.sectionTitle}>
      12-Hour Wait Time Forecast
    </Text>

    <View style={styles.chartRow}>
      {venue.busyness_forecast_12h.map(hour => (
        <View
          key={hour.offset_hours}
          style={styles.chartColumn}
        >
          <View
            style={[
              styles.chartBar,
              {
                height: Math.max(
                  12,
                  hour.percent
                ),
              },
            ]}
          />

          <Text style={styles.chartLabel}>
            +{hour.offset_hours}
          </Text>
        </View>
      ))}
    </View>
  </>
) : (
  <Text style={styles.prediction}>
    Expected wait:
    {" "}
    {venue.avg_wait_minutes}
    {" "}
    minutes
  </Text>
)}

  </>
)}
          <View style={styles.row}>

            <Ionicons
              name="time-outline"
              size={18}
              color={Colours.primary}
            />

            <Text style={styles.rowText}>
              {venue.busyness.estimated_wait_minutes ?? "Unknown"} min wait
            </Text>

          </View>

          <View style={styles.row}>

            <Ionicons
              name="location-outline"
              size={18}
              color={Colours.primary}
            />

            <Text style={styles.rowText}>
              {venue.address}
            </Text>

          </View>

          <View style={styles.row}>

            <Ionicons
              name="call-outline"
              size={18}
              color={Colours.primary}
            />

            <Text style={styles.rowText}>
              {venue.phone}
            </Text>

          </View>

          <TouchableOpacity
            style={styles.directionButton}
          >
            <Ionicons
              name="navigate"
              size={18}
              color="#FFFFFF"
            />

            <Text style={styles.directionText}>
              Directions
            </Text>

          </TouchableOpacity>

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

    marginBottom: 20,

  },

  title: {

    ...Typography.h2,

  },

  address: {

    color: Colours.muted,

    marginTop: 4,

  },

  row: {

    flexDirection: "row",

    alignItems: "center",

    marginBottom: 16,

  },

  rowText: {

    marginLeft: 12,

    color: Colours.text,

    flex: 1,

  },

  directionButton: {

    flexDirection: "row",

    justifyContent: "center",

    alignItems: "center",

    backgroundColor: Colours.primary,

    borderRadius: 16,

    paddingVertical: 16,

    marginTop: 12,

  },

  directionText: {

    color: "#FFFFFF",

    fontWeight: "700",

    marginLeft: 10,

    fontSize: 16,

  },
  alertStrip: {
  flexDirection: "row",
  alignItems: "center",

  backgroundColor: "#DC2626",

  borderRadius: 12,

  paddingVertical: 10,
  paddingHorizontal: 12,

  marginBottom: 20,
},

alertText: {
  color: "#FFFFFF",
  fontWeight: "700",
  marginLeft: 10,
  flex: 1,
},

sectionTitle: {
  marginTop: 18,
  marginBottom: 10,
  fontWeight: "700",
  fontSize: 16,
},

badgeRow: {
  flexDirection: "row",
  flexWrap: "wrap",
  marginBottom: 20,
},

badge: {
  backgroundColor: "#E0F2FE",
  paddingHorizontal: 12,
  paddingVertical: 8,
  borderRadius: 999,
  marginRight: 8,
  marginBottom: 8,
},

badgeText: {
  color: "#0369A1",
  fontWeight: "600",
},

chartRow: {
  flexDirection: "row",
  alignItems: "flex-end",
  justifyContent: "space-between",
  height: 120,
  marginBottom: 16,
},

chartColumn: {
  alignItems: "center",
  flex: 1,
},

chartBar: {
  width: 14,
  borderRadius: 6,
  backgroundColor: Colours.primary,
},

chartLabel: {
  marginTop: 6,
  fontSize: 10,
  color: Colours.muted,
},

prediction: {
  backgroundColor: "#EFF6FF",
  color: "#1D4ED8",
  padding: 14,
  borderRadius: 12,
  fontWeight: "600",
  marginTop: 8,
},
});
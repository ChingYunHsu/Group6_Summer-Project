import { Ionicons } from "@expo/vector-icons";
import { StyleSheet, View } from "react-native";
import { Marker } from "react-native-maps";

import { Venue } from "../types/venue";

interface Props {
  venue: Venue;
  onPress: (venue: Venue) => void;
  showLiveStatus: boolean;
}

const COLOURS = {
  green: "#16A34A",
  yellow: "#FACC15",
  red: "#DC2626",
  blue: "#2563EB",
};

function getMarkerColour(colour?: string) {
  switch (colour) {
    case "green":
      return COLOURS.green;

    case "yellow":
      return COLOURS.yellow;

    case "red":
      return COLOURS.red;

    default:
      return COLOURS.blue;
  }
}

function getMarkerIcon(type: string) {
  switch (type) {
    case "clinic":
      return "medical";

    case "pharmacy":
      return "medkit";

    case "emergencyasset":
      return "heart";

    default:
      return "location";
  }
}

export default function VenueMarker({
  venue,
  showLiveStatus,
  onPress,
}: Props) {
  const background =
  showLiveStatus
    ? getMarkerColour(
        venue.busyness?.busyness_color
      )
    : COLOURS.blue;

  const icon = getMarkerIcon(
    venue.venue_type
  );

  return (
    <Marker
      coordinate={{
        latitude: venue.latitude,
        longitude: venue.longitude,
      }}
      onPress={() => onPress(venue)}
    >
      <View style={styles.wrapper}>
        <View
          style={[
            styles.container,
            {
              backgroundColor: background,
            },
          ]}
        >
          <Ionicons
            name={icon as any}
            size={18}
            color="#FFFFFF"
          />
        </View>

        {venue.active_warning && (
          <View style={styles.warningBadge}>
            <Ionicons
              name="warning"
              size={10}
              color="#000000"
            />
          </View>
        )}
      </View>
    </Marker>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: "relative",
  },

  container: {
    width: 42,
    height: 42,
    borderRadius: 21,

    justifyContent: "center",
    alignItems: "center",

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

  warningBadge: {
    position: "absolute",

    top: -4,
    right: -4,

    width: 18,
    height: 18,

    borderRadius: 9,

    backgroundColor: "#FACC15",

    justifyContent: "center",
    alignItems: "center",

    borderWidth: 2,
    borderColor: "#FFFFFF",

    elevation: 6,
  },
});
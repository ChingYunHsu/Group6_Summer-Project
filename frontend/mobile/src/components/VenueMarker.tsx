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

    case "hospital":
      return "business";

    case "restroom":
      return "male-female";

    // No seeded venues of these three types exist yet — see the
    // VenueCategory comment in types/venue.ts — but these are still
    // valid values per the real venue_type ENUM, so they get real icons
    // rather than silently falling through to the generic default.
    case "healthcare":
      return "medical";

    case "dentist":
      return "medical";

    case "laboratory":
      return "flask";

    default:
      return "location";
  }
}

export default function VenueMarker({ venue, showLiveStatus, onPress }: Props) {
  const background = showLiveStatus
    ? getMarkerColour(venue.busyness?.busyness_color)
    : COLOURS.blue;

  const icon = getMarkerIcon(venue.venue_type);

  return (
    <Marker
      coordinate={{
        // Number(...) matters: the backend sends these as strings (MySQL
        // DECIMAL columns serialize as Decimal -> string via jsonify(),
        // not float), and react-native-maps silently fails to position a
        // marker given string coordinates — no crash, no error, it just
        // never appears. This was the actual reason venues rendered zero
        // markers even after every other bug in this path was fixed.
        latitude: Number(venue.latitude),
        longitude: Number(venue.longitude),
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
          <Ionicons name={icon as any} size={18} color="#FFFFFF" />
        </View>

        {/* Boolean(...) here matters: DB-backed venues can send
            active_warning as a raw MySQL 0/1, not true/false (see
            _row_to_venue() in venues.py — it's missing from that
            function's bool-cast list). `0 && <View />` evaluates to `0`
            in JS, and React Native tries to render that bare 0 as a text
            node, which is exactly the "Text strings must be rendered
            within a <Text> component" crash. Coercing explicitly avoids
            depending on the backend fixing this to not crash. */}
        {Boolean(venue.active_warning) && (
          <View style={styles.warningBadge}>
            <Ionicons name="warning" size={10} color="#000000" />
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

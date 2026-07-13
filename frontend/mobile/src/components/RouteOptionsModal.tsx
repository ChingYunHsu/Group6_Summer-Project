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
import { RouteOption } from "../types/venue";

interface Props {
  visible: boolean;
  routes: RouteOption[];
  originLabel: string;
  departureTime: string;
  selectedMode: string;
  onSelectMode: (mode: string) => void;
  onSelectRoute: (route: RouteOption) => void;
  onClose: () => void;
}

const TABS = [
  {
    label: "Walk",
    mode: "walk",
    icon: "walk-outline",
  },
  {
    label: "Transit",
    mode: "transit",
    icon: "bus-outline",
  },
  {
    label: "Drive",
    mode: "drive",
    icon: "car-outline",
  },
] as const;

export default function RouteOptionsModal({
  visible,
  routes,
  originLabel,
  departureTime,
  selectedMode,
  onSelectMode,
  onSelectRoute,
  onClose,
}: Props) {

  const filteredRoutes = routes.filter(
    route =>
      route.mode.toLowerCase() ===
      selectedMode.toLowerCase()
  );

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
                Route Options
              </Text>

              <Text style={styles.subtitle}>
                {originLabel} • {departureTime}
              </Text>

            </View>

            <TouchableOpacity onPress={onClose}>
              <Ionicons
                name="close"
                size={24}
                color={Colours.text}
              />
            </TouchableOpacity>

          </View>

          <View style={styles.tabRow}>

            {TABS.map(tab => {

              const selected =
                selectedMode === tab.mode;

              return (

                <TouchableOpacity
                  key={tab.mode}
                  style={[
                    styles.tab,
                    selected &&
                      styles.selectedTab,
                  ]}
                  onPress={() =>
                    onSelectMode(tab.mode)
                  }
                >

                  <Ionicons
                    name={tab.icon}
                    size={18}
                    color={
                      selected
                        ? "#FFFFFF"
                        : Colours.primary
                    }
                  />

                  <Text
                    style={[
                      styles.tabText,
                      selected &&
                        styles.selectedTabText,
                    ]}
                  >
                    {tab.label}
                  </Text>

                </TouchableOpacity>

              );

            })}

          </View>

          {filteredRoutes.map(route => (

            <TouchableOpacity
              key={`${route.mode}-${route.summary}`}
              style={styles.card}
              onPress={() =>
                onSelectRoute(route)
              }
            >

              <View style={styles.cardHeader}>

                <View style={{ flex: 1 }}>

                  <Text style={styles.mode}>
                    {route.mode.toUpperCase()}
                  </Text>

                  <Text style={styles.summary}>
                    {route.summary}
                  </Text>

                </View>

                <Text style={styles.duration}>
                  {route.duration_minutes} min
                </Text>

              </View>

              <View style={styles.badgeRow}>

                <View
                  style={[
                    styles.statusBadge,
                    route.status === "available"
                      ? styles.availableBadge
                      : styles.trafficBadge,
                  ]}
                >
                  <Text style={styles.badgeText}>
                    {route.status === "available"
                      ? "Available"
                      : "Moderate Traffic"}
                  </Text>
                </View>

                <View style={styles.accessibilityBadge}>
                  <Text style={styles.accessibilityText}>
                    {route.accessibility_mode === "step_free"
                      ? "Step-Free Accessible"
                      : "Standard Route"}
                  </Text>
                </View>

              </View>

            </TouchableOpacity>

          ))}

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
    maxHeight: "80%",
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
    marginBottom: 20,
  },

  title: {
    ...Typography.h2,
  },

  subtitle: {
    color: Colours.muted,
    marginTop: 4,
    fontSize: 14,
  },

  tabRow: {
    flexDirection: "row",
    marginBottom: 20,
  },

  tab: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colours.primary,
    borderRadius: 12,
    paddingVertical: 12,
    marginHorizontal: 4,
  },

  selectedTab: {
    backgroundColor: Colours.primary,
  },

  tabText: {
    marginLeft: 6,
    color: Colours.primary,
    fontWeight: "600",
  },

  selectedTabText: {
    color: "#FFFFFF",
  },

  card: {
    borderWidth: 1,
    borderColor: "#E5E7EB",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },

  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  mode: {
    color: Colours.primary,
    fontWeight: "700",
    fontSize: 15,
  },

  summary: {
    marginTop: 4,
    color: Colours.text,
  },

  duration: {
    color: Colours.primary,
    fontWeight: "700",
    fontSize: 16,
  },

  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 14,
  },

  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    marginRight: 8,
    marginBottom: 8,
  },

  availableBadge: {
    backgroundColor: "#DCFCE7",
  },

  trafficBadge: {
    backgroundColor: "#FEF3C7",
  },

  badgeText: {
    fontWeight: "600",
    fontSize: 12,
    color: "#166534",
  },

  accessibilityBadge: {
    backgroundColor: "#DBEAFE",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    marginBottom: 8,
  },

  accessibilityText: {
    color: "#1D4ED8",
    fontWeight: "600",
    fontSize: 12,
  },

});
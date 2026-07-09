import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { Report, Venue } from "../types/venue";
import { formatReportedTime } from "./ReportMarker";
import VerificationCard from "./VerificationCard";

interface Props {
  visible: boolean;
  venue: Venue | null;
  // The active report (if any) tied to this venues active_warning flag —
  // passed down from map.tsx, which owns the full reports list. Without
  // this, VerificationCard has no real data to show.
  activeReport?: Report | null;
  autoCurrentTime: boolean;
  onClose: () => void;
  onDirectionsPress: () => void;
  onConfirmReport?: (reportId: string) => void;
  onResolveReport?: (reportId: string) => void;
  // Favourite status is deliberately not read off venue.is_favourite —
  // that field is mock-only (see the Venue type comment) and DB-backed
  // venues dont reliably carry it. map.tsx owns the real favourites list
  // separately and passes the resolved status down.
  isFavourite?: boolean;
  onToggleFavourite?: () => void;
}

export default function VenueBottomSheet({
  visible,
  venue,
  activeReport,
  autoCurrentTime,
  onClose,
  onDirectionsPress,
  onConfirmReport,
  onResolveReport,
  isFavourite = false,
  onToggleFavourite,
}: Props) {
  if (!venue) return null;

  const hasForecast =
    !!venue.busyness_forecast_12h && venue.busyness_forecast_12h.length > 0;

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{venue.name}</Text>

              <Text style={styles.address}>{venue.address}</Text>
            </View>

            {onToggleFavourite && (
              <TouchableOpacity
                onPress={onToggleFavourite}
                style={styles.favouriteButton}
              >
                <Ionicons
                  name={isFavourite ? "heart" : "heart-outline"}
                  size={24}
                  color={isFavourite ? "#DC2626" : Colours.text}
                />
              </TouchableOpacity>
            )}

            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={26} color={Colours.text} />
            </TouchableOpacity>
          </View>
          {/* Boolean(...) here matters — see the comment in
              VenueMarker.tsx: DB-backed venues can send active_warning
              as a raw 0/1 rather than true/false, and `0 && <>...</>`
              would render a bare 0 as a text node and crash. */}
          {Boolean(venue.active_warning) && (
            <>
              <View style={styles.alertStrip}>
                <Ionicons name="warning" size={18} color="#FFFFFF" />

                <Text style={styles.alertText}>
                  Accessibility issue recently reported
                </Text>
              </View>

              {activeReport && (
                <VerificationCard
                  reportedAt={formatReportedTime(activeReport.created_at)}
                  confirmations={activeReport.confirmations.count}
                  onConfirm={() => onConfirmReport?.(activeReport.report_id)}
                  onResolve={() => onResolveReport?.(activeReport.report_id)}
                />
              )}

              <Text style={styles.sectionTitle}>Services</Text>

              <View style={styles.badgeRow}>
                {(venue.supported_services ?? []).map((service) => (
                  <View key={service} style={styles.badge}>
                    <Text style={styles.badgeText}>{service}</Text>
                  </View>
                ))}
              </View>

              {autoCurrentTime ? (
                hasForecast ? (
                  <>
                    <Text style={styles.sectionTitle}>
                      12-Hour Wait Time Forecast
                    </Text>

                    <View style={styles.chartRow}>
                      {venue.busyness_forecast_12h!.map((hour) => (
                        <View
                          key={hour.offset_hours}
                          style={styles.chartColumn}
                        >
                          <View
                            style={[
                              styles.chartBar,
                              {
                                height: Math.max(12, hour.percent),
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
                    Live forecast isn't available for this venue yet.
                  </Text>
                )
              ) : (
                <Text style={styles.prediction}>
                  Expected wait: {venue.avg_wait_minutes ?? "Unknown"} minutes
                </Text>
              )}
            </>
          )}
          <View style={styles.row}>
            <Ionicons name="time-outline" size={18} color={Colours.primary} />

            <Text style={styles.rowText}>
              {venue.busyness?.estimated_wait_minutes ?? "Unknown"} min wait
            </Text>
          </View>

          <View style={styles.row}>
            <Ionicons
              name="location-outline"
              size={18}
              color={Colours.primary}
            />

            <Text style={styles.rowText}>{venue.address}</Text>
          </View>

          <View style={styles.row}>
            <Ionicons name="call-outline" size={18} color={Colours.primary} />

            <Text style={styles.rowText}>{venue.phone}</Text>
          </View>

          <TouchableOpacity
            style={styles.directionButton}
            onPress={onDirectionsPress}
          >
            <Ionicons name="navigate" size={18} color="#FFFFFF" />

            <Text style={styles.directionText}>Directions</Text>
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

  favouriteButton: {
    marginRight: 16,
    justifyContent: "center",
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

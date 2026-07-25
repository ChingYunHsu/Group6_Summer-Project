import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { getVenueBusyness, getVenueForecast } from "../services/api";
import {
  BusynessResponse,
  ForecastResponse,
  Report,
  Venue,
} from "../types/venue";
import { formatReportedTime } from "./ReportMarker";
import VerificationCard from "./VerificationCard";

interface Props {
  visible: boolean;
  venue: Venue | null;
  activeReport?: Report | null;
  autoCurrentTime: boolean;
  timeOffset?: number;
  onClose: () => void;
  onDirectionsPress: () => void;
  onConfirmReport?: (reportId: string) => void;
  onResolveReport?: (reportId: string) => void;
  isFavourite?: boolean;
  onToggleFavourite?: () => void;
}

export default function VenueBottomSheet({
  visible,
  venue,
  activeReport,
  timeOffset = 0,
  onClose,
  onDirectionsPress,
  onConfirmReport,
  onResolveReport,
  isFavourite = false,
  onToggleFavourite,
}: Props) {
  const { t } = useTranslation();

  const formatAddress = (address: string | null | undefined): string => {
    if (!address || /^POINT\s*\(/i.test(address)) {
      return t("venueSheet.addressUnavailable", {
        defaultValue: "Address unavailable",
      });
    }
    return address;
  };

  const [busynessStatus, setBusynessStatus] = useState<BusynessResponse | null>(
    null,
  );

  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  const [busynessLoading, setBusynessLoading] = useState(false);

  useEffect(() => {
    if (!visible || !venue) {
      return;
    }

    let isActive = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag must be set synchronously when the fetch starts, before the async result arrives
    setBusynessLoading(true);

    Promise.all([
      getVenueBusyness(venue.venue_id).catch((error) => {
        console.error("Failed to load venue busyness", error);
        return null;
      }),
      getVenueForecast(venue.venue_id).catch((error) => {
        console.error("Failed to load venue forecast", error);
        return null;
      }),
    ]).then(([busynessResult, forecastResult]) => {
      if (!isActive) return;
      setBusynessStatus(busynessResult);
      setForecast(forecastResult);
      setBusynessLoading(false);
    });

    return () => {
      isActive = false;
      setBusynessStatus(null);
      setForecast(null);
    };
  }, [visible, venue]);

  if (!venue) return null;

  const hasLiveStatus = busynessStatus?.busyness?.data_mode === "forecast";
  const hasForecast =
    forecast?.data_mode === "forecast" && forecast.forecast.length > 0;

  const FORECAST_LEVEL_COLOURS: Record<string, string> = {
    quiet: "green",
    moderate: "yellow",
    busy: "red",
  };

  const selectedForecastEntry =
    hasForecast && timeOffset > 0
      ? forecast?.forecast.find((hour) => hour.offset_hours === timeOffset)
      : null;

  const displayLevel = selectedForecastEntry
    ? selectedForecastEntry.level
    : hasLiveStatus
      ? busynessStatus?.busyness?.busyness_status
      : undefined;

  const displayColour = selectedForecastEntry
    ? FORECAST_LEVEL_COLOURS[selectedForecastEntry.level]
    : hasLiveStatus
      ? busynessStatus?.busyness?.busyness_color
      : undefined;

  const STATUS_LABEL_KEYS: Record<string, { key: string; label: string }> = {
    quiet: { key: "map.filters.quiet", label: "Quiet" },
    moderate: { key: "map.filters.moderate", label: "Moderate" },
    busy: { key: "map.filters.busy", label: "Busy" },
  };

  const displayLabel = displayLevel
    ? t(STATUS_LABEL_KEYS[displayLevel]?.key ?? displayLevel, {
        defaultValue:
          STATUS_LABEL_KEYS[displayLevel]?.label ??
          displayLevel.charAt(0).toUpperCase() + displayLevel.slice(1),
      })
    : null;

  const displayWaitMinutes = selectedForecastEntry
    ? undefined
    : hasLiveStatus
      ? busynessStatus?.busyness?.estimated_wait_minutes
      : undefined;

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{venue.name}</Text>

              <Text style={styles.address}>{formatAddress(venue.address)}</Text>
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

          {displayLabel && displayColour && (
            <View style={styles.statusRow}>
              <View
                style={[styles.statusBadge, { backgroundColor: displayColour }]}
              >
                <View style={styles.statusDot} />

                <Text style={styles.statusText}>
                  {displayLabel}
                  {displayWaitMinutes != null
                    ? t("venueSheet.minWaitSuffix", {
                        defaultValue: " · {{minutes}} min wait",
                        minutes: displayWaitMinutes,
                      })
                    : ""}
                </Text>
              </View>

              {selectedForecastEntry && (
                <Text style={styles.forecastNote}>
                  {t("venueSheet.predictedForHour", {
                    defaultValue: "Predicted for +{{hours}}h — not live data",
                    hours: timeOffset,
                  })}
                </Text>
              )}
            </View>
          )}
          {Boolean(venue.active_warning) && (
            <>
              <View style={styles.alertStrip}>
                <Ionicons name="warning" size={18} color="#FFFFFF" />

                <Text style={styles.alertText}>
                  {t("venueSheet.accessibilityIssue", {
                    defaultValue: "Accessibility issue recently reported",
                  })}
                </Text>
              </View>

              {activeReport && (
                <VerificationCard
                  reportedAt={formatReportedTime(activeReport.created_at, t)}
                  confirmations={activeReport.confirmations.count}
                  onConfirm={() => onConfirmReport?.(activeReport.report_id)}
                  onResolve={() => onResolveReport?.(activeReport.report_id)}
                />
              )}
            </>
          )}

          <View style={styles.row}>
            <Ionicons
              name="accessibility-outline"
              size={18}
              color={
                venue.accessible_status === "full_access" ||
                venue.accessible_status === "partial"
                  ? Colours.primary
                  : Colours.muted
              }
            />

            <Text
              style={[
                styles.rowText,
                venue.accessible_status !== "full_access" &&
                  venue.accessible_status !== "partial" &&
                  styles.unknownText,
              ]}
            >
              {venue.accessible_status === "full_access"
                ? t("venueSheet.fullWheelchairAccess", {
                    defaultValue: "Full wheelchair access",
                  })
                : venue.accessible_status === "partial"
                  ? t("venueSheet.partialWheelchairAccess", {
                      defaultValue: "Partial wheelchair access",
                    })
                  : t("venueSheet.accessibilityUnknown", {
                      defaultValue: "Wheelchair access unknown",
                    })}
            </Text>
          </View>

          {(venue.supported_services ?? []).length > 0 && (
            <>
              <Text style={styles.sectionTitle}>
                {t("venueSheet.services", { defaultValue: "Services" })}
              </Text>
              <View style={styles.amenityGrid}>
                {venue.supported_services!.map((service) => (
                  <View key={service} style={styles.amenityCard}>
                    <View style={styles.amenityCardInner}>
                      <Ionicons
                        name="checkmark-circle-outline"
                        size={22}
                        color={Colours.primary}
                        style={styles.amenityIcon}
                      />

                      <Text style={styles.amenityLabel}>{service}</Text>
                    </View>
                  </View>
                ))}
              </View>
            </>
          )}

          {busynessLoading ? (
            <View style={styles.forecastLoading}>
              <ActivityIndicator size="small" color={Colours.primary} />
            </View>
          ) : hasForecast ? (
            <>
              <Text style={styles.sectionTitle}>
                {t("venueSheet.busynessForecast", {
                  defaultValue: "12-Hour Busyness Forecast",
                })}
              </Text>

              <View style={styles.chartRow}>
                {forecast!.forecast.map((hour) => (
                  <View key={hour.offset_hours} style={styles.chartColumn}>
                    <View
                      style={[
                        styles.chartBar,
                        {
                          height: Math.max(12, hour.percent),
                        },
                      ]}
                    />

                    <Text style={styles.chartLabel}>+{hour.offset_hours}</Text>
                  </View>
                ))}
              </View>
            </>
          ) : (
            <Text style={styles.noLiveInfo}>
              {t("venueSheet.noLiveInfo", { defaultValue: "• No Live Info" })}
            </Text>
          )}

          <View style={styles.row}>
            <Ionicons
              name="location-outline"
              size={18}
              color={Colours.primary}
            />

            <Text style={styles.rowText}>{formatAddress(venue.address)}</Text>
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

            <Text style={styles.directionText}>
              {t("venueSheet.directions", { defaultValue: "Directions" })}
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

  unknownText: {
    color: Colours.muted,
    fontStyle: "italic",
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

  statusRow: {
    marginBottom: 16,
  },

  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },

  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#FFFFFF",
    marginRight: 8,
  },

  statusText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 13,
  },

  forecastNote: {
    marginTop: 6,
    fontSize: 12,
    color: Colours.muted,
    fontStyle: "italic",
  },

  forecastLoading: {
    paddingVertical: 24,
    alignItems: "center",
  },

  sectionTitle: {
    marginTop: 18,
    marginBottom: 10,
    fontWeight: "700",
    fontSize: 16,
  },

  amenityGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginHorizontal: -6,
    marginBottom: 12,
  },

  amenityCard: {
    width: "50%",
    paddingHorizontal: 6,
    marginBottom: 12,
  },

  amenityCardInner: {
    backgroundColor: Colours.surface,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    padding: 14,
  },

  amenityIcon: {
    marginBottom: 10,
  },

  amenityLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: Colours.text,
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

  noLiveInfo: {
    color: Colours.muted,
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 8,
  },
});

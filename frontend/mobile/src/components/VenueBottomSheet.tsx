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
  // The active report (if any) tied to this venues active_warning flag —
  // passed down from map.tsx, which owns the full reports list. Without
  // this, VerificationCard has no real data to show.
  activeReport?: Report | null;
  // No longer read inside this component — the forecast/badge display
  // used to be gated behind this, which meant picking a specific hour
  // via FilterModal's time picker could never show anything (this being
  // false hid the whole section regardless of timeOffset). Still part
  // of the type since map.tsx still passes it; kept here rather than
  // removed from the type entirely to avoid churning map.tsx's call site
  // for something that may still have a real purpose elsewhere.
  autoCurrentTime: boolean;
  // Hours ahead of now (0-11), from FilterModal's real time picker.
  // 0 = Now (live current-status data); 1-11 = look up that hour's
  // entry in the forecast data already being fetched below, rather
  // than making a separate request for it.
  timeOffset?: number;
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
  timeOffset = 0,
  onClose,
  onDirectionsPress,
  onConfirmReport,
  onResolveReport,
  isFavourite = false,
  onToggleFavourite,
}: Props) {
  const { t } = useTranslation();

  // Some restroom source data (confirmed — systematic for the
  // nyc_restrooms source specifically, 349/349 affected, 0/127 for
  // parks_toilets) never got a real street address, and the raw WKT
  // geometry string ended up in the address column instead — e.g.
  // "POINT(-73.9687 40.74809)". Showing that directly to a user looks
  // broken regardless of what eventually fixes it upstream, so this
  // guards against it defensively on the display side. Root cause
  // still needs fixing in the actual ETL loader; this is a display-
  // only safety net, not a substitute for that.
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

  // Fetches only when the sheet actually opens for a real venue — not
  // for every marker on the map, which would mean firing hundreds of
  // requests just to render pins. Both calls run in parallel, and each
  // is caught independently so one failing (e.g. the known current-
  // status bug above) doesn't prevent the other from showing real data.
  useEffect(() => {
    if (!visible || !venue) {
      // Intentional synchronous reset — clears stale busyness/forecast
      // data the moment the sheet closes or switches to a different
      // venue, so a brief flash of the PREVIOUS venue's data can never
      // show while the new fetch is still in flight. Same justified
      // pattern already applied to this identical rule in map.tsx.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBusynessStatus(null);
      setForecast(null);
      return;
    }

    let isActive = true;
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
    };
  }, [visible, venue]);

  if (!venue) return null;

  const hasForecast = !!forecast?.forecast && forecast.forecast.length > 0;

  // No color/color field on forecast entries (unlike the live
  // current-status response, which gets a real one straight from the
  // backend) — this mirrors _level_to_color in venues.py exactly, so
  // predicted-hour colours match what "Now" would show if the backend
  // itself computed them.
  const FORECAST_LEVEL_COLOURS: Record<string, string> = {
    quiet: "green",
    moderate: "yellow",
    busy: "red",
    no_data: "#2563EB",
  };

  const selectedForecastEntry =
    timeOffset > 0
      ? forecast?.forecast.find((hour) => hour.offset_hours === timeOffset)
      : null;

  const displayLevel =
    selectedForecastEntry?.level ?? busynessStatus?.busyness?.busyness_status;

  const displayColour = selectedForecastEntry
    ? (FORECAST_LEVEL_COLOURS[selectedForecastEntry.level] ??
      FORECAST_LEVEL_COLOURS.no_data)
    : busynessStatus?.busyness?.busyness_color;

  // Status labels ("Quiet"/"Moderate"/"Busy") come from the backend as
  // lowercase level strings — translated via a lookup rather than just
  // capitalizing the raw value, since "quiet"/"moderate"/"busy" need
  // real translations, not just a capital letter, in other languages.
  const STATUS_LABEL_KEYS: Record<string, { key: string; label: string }> = {
    quiet: { key: "map.filters.quiet", label: "Quiet" },
    moderate: { key: "map.filters.moderate", label: "Moderate" },
    busy: { key: "map.filters.busy", label: "Busy" },
    no_data: { key: "venueSheet.noData", label: "No data" },
  };

  const displayLabel = displayLevel
    ? t(STATUS_LABEL_KEYS[displayLevel]?.key ?? "venueSheet.noData", {
        defaultValue:
          STATUS_LABEL_KEYS[displayLevel]?.label ??
          displayLevel.charAt(0).toUpperCase() + displayLevel.slice(1),
      })
    : null;

  // Wait-minutes are only ever known for live ("Now") status —
  // VenueForecast (the type behind forecast entries) has no wait-
  // minutes field at all, only percent/level. Showing a real number for
  // "Now" but omitting it entirely for a predicted hour keeps this
  // honest about what's actually known vs predicted, rather than
  // fabricating a figure that was never really calculated.
  const displayWaitMinutes = selectedForecastEntry
    ? undefined
    : busynessStatus?.busyness?.estimated_wait_minutes;

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

          {/* Real status pill — matches the original Stitch mockup's
              "Quiet - 5 min wait" badge. Only renders once real data
              actually exists; no fabricated "no_data" pill shown while
              loading or if the current-status fetch comes back empty
              (a real, known possibility — see the effect above). When
              a future hour is selected via the time picker, this shows
              that hour's predicted level instead of live status. */}
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
          {/* Boolean(...) here matters — see the comment in
              VenueMarker.tsx: DB-backed venues can send active_warning
              as a raw 0/1 rather than true/false, and `0 && <>...</>`
              would render a bare 0 as a text node and crash. */}
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
                  reportedAt={formatReportedTime(activeReport.created_at)}
                  confirmations={activeReport.confirmations.count}
                  onConfirm={() => onConfirmReport?.(activeReport.report_id)}
                  onResolve={() => onResolveReport?.(activeReport.report_id)}
                />
              )}
            </>
          )}

          {/* Bug fix: this used to be nested inside the active_warning
              block above, meaning Services and the forecast chart only
              ever showed for venues currently flagged with a warning —
              every other venue showed neither at all. Both are now
              unconditional, matching the mockup's intent. */}

          {(venue.supported_services ?? []).length > 0 && (
            <>
              <Text style={styles.sectionTitle}>
                {t("venueSheet.services", { defaultValue: "Services" })}
              </Text>

              {/* 2x2 card grid, replacing the previous pill-badge row —
                  matches the mockup's visual style. Sourced from the
                  same real venue.supported_services data as before, not
                  hardcoded — a venue only shows what it actually has,
                  rather than claiming fixed features (like "Elevator
                  Working") that may not be true for every location. */}
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

          {/* No longer gated behind autoCurrentTime — that toggle is a
              separate, unrelated concept (originally meant for something
              else entirely) that had nothing to do with whether real
              forecast data exists. Gating this section behind it meant
              picking a specific hour via FilterModal's time picker could
              never actually show anything, since autoCurrentTime being
              false hid this whole section regardless of what timeOffset
              was. Now this shows purely based on whether real data
              exists — loading, has real data, or genuinely doesn't yet —
              and the chart always shows the full 12-hour spread
              regardless of which specific hour is selected; the status
              badge above is what reflects the selected hour specifically. */}
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
            <Text style={styles.prediction}>
              {t("venueSheet.forecastUnavailable", {
                defaultValue:
                  "Live forecast isn't available for this venue yet.",
              })}
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

  prediction: {
    backgroundColor: "#EFF6FF",
    color: "#1D4ED8",
    padding: 14,
    borderRadius: 12,
    fontWeight: "600",
    marginTop: 8,
  },
});

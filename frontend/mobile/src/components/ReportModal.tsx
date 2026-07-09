import { useMemo, useState } from "react";

import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

import { Venue } from "../types/venue";

interface Props {
  visible: boolean;

  isAuthenticated: boolean;
  locationEnabled: boolean;

  currentLocation: {
    latitude: number;
    longitude: number;
  };

  nearbyVenues: Venue[];

  onClose: () => void;

  onRequireLogin: () => void;

  onRequireLocation: () => void;

  onSubmitVenue: (report: {
    venueId: string;
    issueType: string;
    description: string;
    timestamp: string;
    // Required: submit_report() on the backend rejects any payload missing
    // latitude/longitude, venue-bound or not. Sourced from the selected
    // venue's own coordinates rather than the user's current location.
    latitude: number;
    longitude: number;
  }) => void;

  onSubmitIncident: (report: {
    latitude: number;
    longitude: number;
    issueType: string;
    description: string;
    timestamp: string;
  }) => void;
}

type ReportMode = "venue" | "incident" | null;

const ISSUE_TYPES = [
  {
    label: "reportModal.issueTypes.largeCrowd",
    value: "large_crowd",
    icon: "people",
  },
  {
    label: "reportModal.issueTypes.entranceClosed",
    value: "entrance_closed",
    icon: "close-circle",
  },
  {
    label: "reportModal.issueTypes.elevatorBroken",
    value: "elevator_broken",
    icon: "warning",
  },
  {
    label: "reportModal.issueTypes.wheelchairLiftBroken",
    value: "wheelchair_lift_broken",
    icon: "construct",
  },
  {
    label: "reportModal.issueTypes.toiletOutOfOrder",
    value: "toilet_out_of_order",
    icon: "ban",
  },
  {
    label: "reportModal.issueTypes.protestOrBlockage",
    value: "protest_or_blockage",
    icon: "alert-circle",
  },
] as const;

const ISSUE_FILTERS = {
  clinic: [
    "large_crowd",
    "entrance_closed",
    "elevator_broken",
    "wheelchair_lift_broken",
    "toilet_out_of_order",
    "protest_or_blockage",
  ],

  hospital: [
    "large_crowd",
    "entrance_closed",
    "elevator_broken",
    "wheelchair_lift_broken",
    "toilet_out_of_order",
    "protest_or_blockage",
  ],

  toilet: ["toilet_out_of_order", "entrance_closed"],

  transport: ["large_crowd", "entrance_closed", "protest_or_blockage"],

  building: ["entrance_closed", "elevator_broken", "wheelchair_lift_broken"],
};

export default function ReportModal({
  visible,
  onClose,

  isAuthenticated,
  locationEnabled,

  currentLocation,

  nearbyVenues,

  onRequireLogin,
  onRequireLocation,

  onSubmitVenue,
  onSubmitIncident,
}: Props) {
  const { t } = useTranslation();

  const [mode, setMode] = useState<ReportMode>(null);

  const [selectedVenue, setSelectedVenue] = useState<string>("");

  const [issueType, setIssueType] = useState("");

  const [description, setDescription] = useState("");

  const selectedVenueObject = nearbyVenues.find(
    (v) => v.venue_id === selectedVenue,
  );

  const visibleIssues = useMemo(() => {
    if (mode !== "venue") {
      return ISSUE_TYPES;
    }

    if (!selectedVenueObject) {
      return [];
    }

    const venueType =
      selectedVenueObject.venue_type as keyof typeof ISSUE_FILTERS;

    const allowed = ISSUE_FILTERS[venueType] ?? ISSUE_TYPES.map((i) => i.value);

    return ISSUE_TYPES.filter((issue) => allowed.includes(issue.value));
  }, [mode, selectedVenueObject]);

  const resetState = () => {
    setMode(null);
    setSelectedVenue("");
    setIssueType("");
    setDescription("");
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleSubmit = () => {
    if (!isAuthenticated) {
      Alert.alert(
        t("reportModal.loginRequired"),
        t("reportModal.loginRequiredMessage"),
        [
          {
            text: t("login.signIn"),
            onPress: () => {
              handleClose();
              onRequireLogin();
            },
          },
        ],
      );

      return;
    }

    if (!locationEnabled) {
      Alert.alert(
        t("reportModal.locationRequired"),
        t("reportModal.locationRequiredMessage"),
        [
          {
            text: t("common.continue"),
            onPress: onRequireLocation,
          },
        ],
      );

      return;
    }

    if (!mode) {
      return;
    }

    if (!issueType) {
      return;
    }

    const timestamp = new Date().toISOString();

    if (mode === "venue") {
      if (!selectedVenue || !selectedVenueObject) {
        return;
      }

      onSubmitVenue({
        venueId: selectedVenue,

        issueType,

        description,

        timestamp,

        latitude: selectedVenueObject.latitude,

        longitude: selectedVenueObject.longitude,
      });
    } else {
      onSubmitIncident({
        latitude: currentLocation.latitude,

        longitude: currentLocation.longitude,

        issueType,

        description,

        timestamp,
      });
    }

    handleClose();
  };
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />

          <View style={styles.header}>
            <Text style={styles.title}>{t("reportModal.title")} </Text>

            <TouchableOpacity onPress={handleClose}>
              <Ionicons name="close" size={26} color={Colours.text} />
            </TouchableOpacity>
          </View>

          <Text style={styles.subtitle}>{t("reportModal.subtitle")}</Text>

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* ------------------------- */}
            {/* STEP 1 */}
            {/* ------------------------- */}

            <Text style={styles.sectionTitle}>
              {t("reportModal.whereIsIssue")}
            </Text>

            <View style={styles.modeContainer}>
              <TouchableOpacity
                style={[
                  styles.modeCard,
                  mode === "venue" && styles.selectedCard,
                ]}
                onPress={() => setMode("venue")}
              >
                <Ionicons
                  name="business"
                  size={28}
                  color={mode === "venue" ? "#FFFFFF" : Colours.primary}
                />

                <Text
                  style={[
                    styles.cardText,
                    mode === "venue" && styles.selectedCardText,
                  ]}
                >
                  {t("reportModal.nearbyVenue")}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modeCard,
                  mode === "incident" && styles.selectedCard,
                ]}
                onPress={() => setMode("incident")}
              >
                <Ionicons
                  name="location"
                  size={28}
                  color={mode === "incident" ? "#FFFFFF" : Colours.primary}
                />

                <Text
                  style={[
                    styles.cardText,
                    mode === "incident" && styles.selectedCardText,
                  ]}
                >
                  {t("reportModal.currentLocation")}
                </Text>
              </TouchableOpacity>
            </View>

            {/* ------------------------- */}
            {/* STEP 2 */}
            {/* ------------------------- */}

            {mode === "venue" && (
              <>
                <Text style={styles.sectionTitle}>
                  {t("reportModal.selectVenue")}
                </Text>

                {nearbyVenues.map((venue) => {
                  const selected = selectedVenue === venue.venue_id;

                  return (
                    <TouchableOpacity
                      key={venue.venue_id}
                      style={[
                        styles.venueRow,
                        selected && styles.selectedVenue,
                      ]}
                      onPress={() => setSelectedVenue(venue.venue_id)}
                    >
                      <View>
                        <Text style={styles.venueName}>{venue.name}</Text>

                        <Text style={styles.venueDistance}>
                          {t("reportModal.nearby")}
                        </Text>
                      </View>

                      {selected && (
                        <Ionicons
                          name="checkmark-circle"
                          size={24}
                          color={Colours.primary}
                        />
                      )}
                    </TouchableOpacity>
                  );
                })}
              </>
            )}

            {/* ------------------------- */}
            {/* STEP 3 */}
            {/* ------------------------- */}

            {mode !== null && (
              <>
                <Text style={styles.sectionTitle}>
                  {t("reportModal.issueType")}
                </Text>

                <View style={styles.grid}>
                  {visibleIssues.map((item) => {
                    const selected = issueType === item.value;

                    return (
                      <TouchableOpacity
                        key={item.value}
                        style={[styles.card, selected && styles.selectedCard]}
                        onPress={() => setIssueType(item.value)}
                      >
                        <Ionicons
                          name={item.icon as any}
                          size={22}
                          color={selected ? "#FFFFFF" : Colours.primary}
                        />

                        <Text
                          style={[
                            styles.cardText,
                            selected && styles.selectedCardText,
                          ]}
                        >
                          {t(item.label)}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                <TextInput
                  style={styles.input}
                  placeholder={t("reportModal.additionalInformation")}
                  placeholderTextColor={Colours.muted}
                  multiline
                  value={description}
                  onChangeText={setDescription}
                />

                <Text style={styles.footnote}>
                  {t("reportModal.timestampNotice")}
                </Text>

                <TouchableOpacity
                  style={[
                    styles.submitButton,
                    (!issueType || (mode === "venue" && !selectedVenue)) &&
                      styles.disabledButton,
                  ]}
                  disabled={!issueType || (mode === "venue" && !selectedVenue)}
                  onPress={handleSubmit}
                >
                  <Ionicons name="warning" size={20} color="#FFFFFF" />

                  <Text style={styles.submitText}>
                    {t("reportModal.submit")}
                  </Text>
                </TouchableOpacity>
              </>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.35)",
  },

  sheet: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 24,
    paddingTop: 18,
    paddingBottom: 32,
    maxHeight: "92%",
  },

  handle: {
    width: 48,
    height: 5,
    borderRadius: 999,
    backgroundColor: "#D1D5DB",
    alignSelf: "center",
    marginBottom: 20,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },

  title: {
    ...Typography.h2,
  },

  subtitle: {
    color: Colours.muted,
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 22,
  },

  sectionTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: Colours.text,
    marginBottom: 12,
    marginTop: 10,
  },

  modeContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
  },

  modeCard: {
    width: "48%",
    backgroundColor: Colours.surface,
    borderRadius: 18,
    paddingVertical: 20,
    paddingHorizontal: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "transparent",
  },

  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 8,
  },

  card: {
    width: "48%",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 12,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
    borderWidth: 2,
    borderColor: "transparent",
  },

  selectedCard: {
    backgroundColor: Colours.primary,
    borderColor: Colours.primary,
  },

  cardText: {
    marginTop: 10,
    textAlign: "center",
    fontWeight: "600",
    fontSize: 14,
    color: Colours.text,
  },

  selectedCardText: {
    color: "#FFFFFF",
  },

  venueRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: Colours.surface,
    paddingHorizontal: 18,
    paddingVertical: 16,
    borderRadius: 16,
    marginBottom: 10,
    borderWidth: 2,
    borderColor: "transparent",
  },

  selectedVenue: {
    borderColor: Colours.primary,
    backgroundColor: "#FFF9E8",
  },

  venueName: {
    fontSize: 16,
    fontWeight: "700",
    color: Colours.text,
  },

  venueDistance: {
    marginTop: 4,
    fontSize: 13,
    color: Colours.muted,
  },

  input: {
    minHeight: 110,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginTop: 12,
    color: Colours.text,
    textAlignVertical: "top",
    fontSize: 15,
    marginBottom: 10,
  },

  footnote: {
    textAlign: "center",
    fontSize: 12,
    color: Colours.muted,
    marginBottom: 18,
    fontStyle: "italic",
  },

  submitButton: {
    backgroundColor: Colours.primary,
    borderRadius: 18,
    paddingVertical: 17,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    marginTop: 6,
  },

  disabledButton: {
    opacity: 0.45,
  },

  submitText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
    marginLeft: 8,
  },
});

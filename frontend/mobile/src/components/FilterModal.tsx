import { useEffect, useRef, useState } from "react";

import {
  Modal,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { featuredLanguages } from "../data/languages";

interface Props {
  visible: boolean;
  openNow?: boolean;
  accessible?: boolean;
  language: string;
  autoCurrentTime: boolean;
  onClose: () => void;
  onApply: (filters: {
    openNow: boolean;
    accessible: boolean;
    language: string;
    autoCurrentTime: boolean;
    liveStatus: "quiet" | "moderate" | "busy";
    date: string;
    time: string;
  }) => void;
}
const LANGUAGE_OPTIONS = featuredLanguages
  .filter((l) => l.code !== "en")
  .map((l) => ({ label: l.english, code: l.code }));

const LIVE_STATUS = [
  { label: "Quiet", value: "quiet" },
  { label: "Moderate", value: "moderate" },
  { label: "Busy", value: "busy" },
] as const;

const STATUS_COLOURS = {
  quiet: "#006400",
  moderate: "#F59E0B",
  busy: "#DC2626",
};

export default function FilterModal({
  visible,
  openNow,
  accessible,
  language,
  autoCurrentTime: autoCurrentTimeProp,
  onClose,
  onApply,
}: Props) {
  const [localOpenNow, setLocalOpenNow] = useState(openNow ?? false);
  const [localAccessible, setLocalAccessible] = useState(accessible ?? false);
  const [localLanguage, setLocalLanguage] = useState(language);
  const [autoCurrentTime, setAutoCurrentTime] = useState(autoCurrentTimeProp);
  const [liveStatus, setLiveStatus] = useState<"quiet" | "moderate" | "busy">(
    "moderate",
  );

  const [date] = useState("Today");
  const [time] = useState("Now");

  // Re-sync draft (local*) state from props, but ONLY on a genuine reopen
  // (visible transitioning false -> true) — not on initial mount, since
  // the useState initializers above already seed the correct values then.
  // Firing this unconditionally on every mount previously created a race
  // with in-modal interactions (e.g. toggling Auto Current Time): the
  // effect's first run could land after the switch's onValueChange and
  // silently stomp the just-toggled value back to the original prop,
  // which is exactly what broke the toggle-interaction tests.
  const prevVisibleRef = useRef(visible);

  useEffect(() => {
    const justOpened = visible && !prevVisibleRef.current;
    prevVisibleRef.current = visible;

    if (!justOpened) return;

    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: resync local draft state only when the modal is reopened
    setLocalOpenNow(openNow ?? false);
    setLocalAccessible(accessible ?? false);
    setLocalLanguage(language);
    setAutoCurrentTime(autoCurrentTimeProp);
  }, [visible, openNow, accessible, language, autoCurrentTimeProp]);

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <View style={styles.header}>
            <Text style={styles.title}>Filters</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} color={Colours.text} />
            </TouchableOpacity>
          </View>

          <Text style={styles.section}>Availability</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Open Now</Text>
            <Switch value={localOpenNow} onValueChange={setLocalOpenNow} />
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Accessible</Text>
            <Switch
              value={localAccessible}
              onValueChange={setLocalAccessible}
            />
          </View>

          <Text style={styles.section}>Time</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Auto Current Time</Text>
            <Switch
              testID="auto-current-time-switch"
              value={autoCurrentTime}
              onValueChange={setAutoCurrentTime}
              trackColor={{ false: "#D1D5DB", true: Colours.primary }}
              thumbColor="#FFFFFF"
            />
          </View>

          {autoCurrentTime ? (
            <>
              <Text style={styles.section}>Live Status</Text>
              <View testID="live-status-section" style={styles.chipRow}>
                {LIVE_STATUS.map((item) => {
                  const selected = item.value === liveStatus;
                  return (
                    <TouchableOpacity
                      key={item.value}
                      style={[
                        styles.chip,
                        selected && {
                          backgroundColor: STATUS_COLOURS[item.value],
                        },
                      ]}
                      onPress={() => setLiveStatus(item.value)}
                    >
                      <Text
                        style={[
                          styles.chipText,
                          selected && styles.selectedText,
                        ]}
                      >
                        {item.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </>
          ) : (
            <>
              <TouchableOpacity testID="date-selector" style={styles.dateRow}>
                <Ionicons
                  name="calendar-outline"
                  size={18}
                  color={Colours.primary}
                />
                <Text style={styles.dateText}>{date}</Text>
                <Ionicons
                  name="chevron-forward"
                  size={18}
                  color="#9CA3AF"
                  style={styles.chevron}
                />
              </TouchableOpacity>
              <TouchableOpacity testID="time-selector" style={styles.dateRow}>
                <Ionicons
                  name="time-outline"
                  size={18}
                  color={Colours.primary}
                />
                <Text style={styles.dateText}>{time}</Text>
                <Ionicons
                  name="chevron-forward"
                  size={18}
                  color="#9CA3AF"
                  style={styles.chevron}
                />
              </TouchableOpacity>
            </>
          )}

          <Text style={styles.section}>Language</Text>
          <View style={styles.chipRow}>
            {LANGUAGE_OPTIONS.map((item) => {
              const selected = item.code === localLanguage;
              return (
                <TouchableOpacity
                  key={item.code}
                  style={[styles.chip, selected && styles.selectedChip]}
                  onPress={() => setLocalLanguage(item.code)}
                >
                  <Text
                    style={[styles.chipText, selected && styles.selectedText]}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <TouchableOpacity
            testID="apply-filters-button"
            style={styles.applyButton}
            onPress={() => {
              onApply({
                openNow: localOpenNow,
                accessible: localAccessible,
                language: localLanguage,
                autoCurrentTime,
                liveStatus,
                date,
                time,
              });
              onClose();
            }}
          >
            <Text style={styles.applyText}>Apply Filters</Text>
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
    backgroundColor: "rgba(0,0,0,0.3)",
  },
  sheet: {
    backgroundColor: "#FFF",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
  },
  handle: {
    width: 50,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#D1D5DB",
    alignSelf: "center",
    marginBottom: 20,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  title: { ...Typography.h2 },
  section: {
    fontWeight: "700",
    marginBottom: 12,
    marginTop: 12,
    color: Colours.text,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  label: { fontSize: 16, color: Colours.text },
  chipRow: { flexDirection: "row", flexWrap: "wrap", marginBottom: 20 },
  chip: {
    borderRadius: 999,
    backgroundColor: Colours.surface,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginRight: 10,
    marginBottom: 10,
  },
  selectedChip: { backgroundColor: Colours.primary },
  chipText: { color: Colours.text, fontWeight: "600" },
  selectedText: { color: "#FFF" },
  dateRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surface,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  dateText: { marginLeft: 12, color: Colours.text, fontSize: 16 },
  chevron: { marginLeft: "auto" },
  applyButton: {
    backgroundColor: Colours.primary,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 10,
  },
  applyText: { color: "#FFF", fontSize: 16, fontWeight: "700" },
});

import { useEffect, useRef, useState } from "react";

import {
  Modal,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

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
    openNow: boolean | undefined;
    accessible: boolean | undefined;
    language: string;
    autoCurrentTime: boolean;
    liveStatus: "quiet" | "moderate" | "busy" | undefined;
    date: string;
    time: string;
    timeOffset: number;
  }) => void;
}
const LANGUAGE_OPTIONS = featuredLanguages
  .filter((l) => l.code !== "en")
  .map((l) => ({ label: l.english, code: l.code }));

// value stays the stable internal value used in state/onApply — the
// display label is now looked up via translationKey at render time.
const LIVE_STATUS = [
  {
    translationKey: "map.filters.quiet",
    defaultValue: "Quiet",
    value: "quiet",
  },
  {
    translationKey: "map.filters.moderate",
    defaultValue: "Moderate",
    value: "moderate",
  },
  {
    translationKey: "map.filters.busy",
    defaultValue: "Busy",
    value: "busy",
  },
] as const;

const STATUS_COLOURS = {
  quiet: "#006400",
  moderate: "#F59E0B",
  busy: "#DC2626",
};

const TIME_OFFSET_OPTIONS = Array.from({ length: 12 }, (_, i) => i);

export default function FilterModal({
  visible,
  openNow,
  accessible,
  language,
  autoCurrentTime: autoCurrentTimeProp,
  onClose,
  onApply,
}: Props) {
  const { t } = useTranslation();

  const [localOpenNow, setLocalOpenNow] = useState(openNow ?? false);
  const [localAccessible, setLocalAccessible] = useState(accessible ?? false);
  const [localLanguage, setLocalLanguage] = useState(language);
  const [autoCurrentTime, setAutoCurrentTime] = useState(autoCurrentTimeProp);
  // Starts unselected (undefined), not defaulted to "moderate" — Live
  // Status is meant to be an optional filter, not a required choice.
  const [liveStatus, setLiveStatus] = useState<
    "quiet" | "moderate" | "busy" | undefined
  >(undefined);

  // "Today" stays permanently fixed — there's no multi-day forecast data
  // anywhere to pick from, only a rolling 12-hour window from now. Kept
  // as a plain string for the (currently unused, but still typed)
  // onApply payload field.
  const [date] = useState("Today");

  // The real, working picker — 0 = Now (live status), 1-11 = hours
  // ahead, matching offset_hours in the forecast data already fetched
  // by VenueBottomSheet.
  const [timeOffset, setTimeOffset] = useState(0);
  const [timeModalVisible, setTimeModalVisible] = useState(false);

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
            <Text style={styles.title}>
              {t("map.filters.title", { defaultValue: "Filters" })}
            </Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} color={Colours.text} />
            </TouchableOpacity>
          </View>

          <Text style={styles.section}>
            {t("map.filters.availability", { defaultValue: "Availability" })}
          </Text>
          <View style={styles.row}>
            <Text style={styles.label}>
              {t("map.filters.openNow", { defaultValue: "Open Now" })}
            </Text>
            <Switch value={localOpenNow} onValueChange={setLocalOpenNow} />
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>
              {t("map.filters.accessible", { defaultValue: "Accessible" })}
            </Text>
            <Switch
              value={localAccessible}
              onValueChange={setLocalAccessible}
            />
          </View>
          <Text style={styles.section}>
            {t("map.filters.time", { defaultValue: "Time" })}
          </Text>
          <View style={styles.row}>
            <Text style={styles.label}>
              {t("map.filters.autoCurrentTime", {
                defaultValue: "Auto Current Time",
              })}
            </Text>
            <Switch
              testID="auto-current-time-switch"
              value={autoCurrentTime}
              onValueChange={(value) => {
                setAutoCurrentTime(value);
              }}
            />
          </View>

          <Text style={styles.section}>
            {t("map.filters.liveStatus", { defaultValue: "Live Status" })}
          </Text>
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
                  onPress={() =>
                    setLiveStatus(selected ? undefined : item.value)
                  }
                >
                  <Text
                    style={[styles.chipText, selected && styles.selectedText]}
                  >
                    {t(item.translationKey, {
                      defaultValue: item.defaultValue,
                    })}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Deliberately a plain View, not TouchableOpacity — no
              chevron either. There's no multi-day forecast data to
              pick from, only a rolling 12-hour window from now, so
              this should visually read as fixed, not as a control
              that just happens to not respond. */}
          <View testID="date-selector" style={styles.dateRow}>
            <Ionicons
              name="calendar-outline"
              size={18}
              color={Colours.primary}
            />
            <Text style={styles.dateText}>
              {t("map.filters.dateToday", { defaultValue: "Today" })}
            </Text>
          </View>

          <TouchableOpacity
            testID="time-selector"
            style={styles.dateRow}
            onPress={() => setTimeModalVisible(true)}
          >
            <Ionicons name="time-outline" size={18} color={Colours.primary} />
            <Text style={styles.dateText}>
              {timeOffset === 0
                ? t("map.filters.timeNow", { defaultValue: "Now" })
                : t("map.filters.timeOffset", {
                    defaultValue: "+{{hours}}h",
                    hours: timeOffset,
                  })}
            </Text>
            <Ionicons
              name="chevron-forward"
              size={18}
              color="#9CA3AF"
              style={styles.chevron}
            />
          </TouchableOpacity>

          <Text style={styles.section}>
            {t("map.filters.language", { defaultValue: "Language" })}
          </Text>
          <View style={styles.chipRow}>
            {LANGUAGE_OPTIONS.map((item) => {
              const selected = item.code === localLanguage;
              return (
                <TouchableOpacity
                  key={item.code}
                  style={[styles.chip, selected && styles.selectedChip]}
                  onPress={() => setLocalLanguage(selected ? "" : item.code)}
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
                // localOpenNow/localAccessible are always real booleans
                // internally (Switch needs that), but the API treats
                // false as an EXPLICIT filter ("only show closed venues")
                // not "no preference" — sending false unconditionally
                // meant the very first time this modal was applied at
                // all, even untouched switches silently turned into a
                // real, restrictive filter instead of staying off.
                // || undefined converts a false switch back into "no
                // preference", only sending true when actually toggled on.
                openNow: localOpenNow || undefined,
                accessible: localAccessible || undefined,
                language: localLanguage,
                autoCurrentTime,
                liveStatus,
                date,
                time: timeOffset === 0 ? "Now" : `+${timeOffset}h`,
                timeOffset,
              });
              onClose();
            }}
          >
            <Text style={styles.applyText}>
              {t("map.filters.apply", { defaultValue: "Apply Filters" })}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Conditional overlay, not a second <Modal> — iOS genuinely
            cannot present two native Modal components at the same
            time; the second one silently fails to appear with no JS-
            visible error at all (confirmed: a real, well-documented
            React Native/iOS limitation, not a bug in this specific
            code). Rendering this inside the SAME Modal that's already
            open sidesteps the limitation entirely. */}
        {timeModalVisible && (
          <View style={styles.pickerOverlay}>
            <View style={styles.pickerCard}>
              <Text style={styles.pickerTitle}>
                {t("map.filters.selectTime", { defaultValue: "Select Time" })}
              </Text>
              <ScrollView style={styles.pickerList}>
                {TIME_OFFSET_OPTIONS.map((offset) => {
                  const selected = offset === timeOffset;

                  return (
                    <TouchableOpacity
                      key={offset}
                      style={styles.pickerRow}
                      onPress={() => {
                        setTimeOffset(offset);
                        setTimeModalVisible(false);
                      }}
                    >
                      <Text style={styles.pickerRowText}>
                        {offset === 0
                          ? t("map.filters.timeNow", { defaultValue: "Now" })
                          : t("map.filters.timeOffset", {
                              defaultValue: "+{{hours}}h",
                              hours: offset,
                            })}
                      </Text>

                      {selected && (
                        <Ionicons
                          name="checkmark"
                          size={20}
                          color={Colours.primary}
                        />
                      )}
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>

              <TouchableOpacity onPress={() => setTimeModalVisible(false)}>
                <Text style={styles.pickerCancel}>
                  {t("common.cancel", { defaultValue: "Cancel" })}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
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

  pickerOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.3)",
  },
  pickerCard: {
    backgroundColor: "#FFF",
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
  },
  pickerTitle: { ...Typography.h2, marginBottom: 16 },
  pickerList: { maxHeight: 320, marginBottom: 12 },
  pickerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
  },
  pickerRowText: { fontSize: 16, color: Colours.text },
  pickerCancel: {
    textAlign: "center",
    color: Colours.muted,
    fontSize: 16,
    paddingVertical: 8,
  },
});

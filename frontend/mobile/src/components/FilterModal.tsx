import { useEffect, useState } from "react";

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

interface Props {
  visible: boolean;

  openNow: boolean;

  accessible: boolean;

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

const LANGUAGES = [
  "French",
  "Spanish",
  "Chinese",
  "German",
  "Italian",
];

const LIVE_STATUS = [
  {
    label: "Quiet",
    value: "quiet",
  },
  {
    label: "Moderate",
    value: "moderate",
  },
  {
    label: "Busy",
    value: "busy",
  },
] as const;

const STATUS_COLOURS = {
  quiet: "#006400",
  moderate: "#F59E0B",
  busy: "#DC2626",
}

export default function FilterModal({
  visible,
  openNow,
  accessible,
  language,
  autoCurrentTime: autoCurrentTimeProp,
  onClose,
  onApply,
}: Props) {
  const [localOpenNow, setLocalOpenNow] =
    useState(openNow);

  const [
    localAccessible,
    setLocalAccessible,
  ] = useState(accessible);

  const [
    localLanguage,
    setLocalLanguage,
  ] = useState(language);

  const [
    autoCurrentTime,
    setAutoCurrentTime,
  ] = useState(autoCurrentTimeProp);

  const [
    liveStatus,
    setLiveStatus,
  ] = useState<
    "quiet" | "moderate" | "busy"
  >("moderate");

  // Placeholder values until
  // real date/time picker is added

  const [date] = useState(
    "Today"
  );

  const [time] = useState(
    "Now"
  );

  useEffect(() => {
    setLocalOpenNow(openNow);

    setLocalAccessible(
      accessible
    );

    setLocalLanguage(
      language
    );

    setAutoCurrentTime(
      autoCurrentTimeProp
    );
  }, [
    visible,
    openNow,
    accessible,
    language,
    autoCurrentTimeProp,
  ]);

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
            <Text style={styles.title}>
              Filters
            </Text>

            <TouchableOpacity
              onPress={onClose}
            >
              <Ionicons
                name="close"
                size={24}
                color={
                  Colours.text
                }
              />
            </TouchableOpacity>
          </View>

          {/* Availability */}

          <Text
            style={styles.section}
          >
            Availability
          </Text>

          <View style={styles.row}>
            <Text
              style={styles.label}
            >
              Open Now
            </Text>

            <Switch
              value={
                localOpenNow
              }
              onValueChange={
                setLocalOpenNow
              }
            />
          </View>

          <View style={styles.row}>
            <Text
              style={styles.label}
            >
              Accessible
            </Text>

            <Switch
              value={
                localAccessible
              }
              onValueChange={
                setLocalAccessible
              }
            />
          </View>

          {/* Time */}

          <Text
            style={styles.section}
          >
            Time
          </Text>

          <View style={styles.row}>
            <Text
              style={styles.label}
            >
              Auto Current Time
            </Text>

            <Switch
  value={autoCurrentTime}
  onValueChange={setAutoCurrentTime}
  trackColor={{
    false: "#D1D5DB",
    true: Colours.primary,
  }}
  thumbColor="#FFFFFF"
/>
          </View>

          {autoCurrentTime ? (
            <>
              <Text
                style={
                  styles.section
                }
              >
                Live Status
              </Text>

              <View
                style={
                  styles.chipRow
                }
              >
                {LIVE_STATUS.map(
                  (
                    item
                  ) => {
                    const selected =
                      item.value ===
                      liveStatus;

                    return (
                      <TouchableOpacity
                        key={
                          item.value
                        }
                        style={[
  styles.chip,
  selected && {
    backgroundColor:
      STATUS_COLOURS[item.value],
  },
]}
                        onPress={() =>
                          setLiveStatus(
                            item.value
                          )
                        }
                      >
                        <Text
                          style={[
                            styles.chipText,
                            selected &&
                              styles.selectedText,
                          ]}
                        >
                          {
                            item.label
                          }
                        </Text>
                      </TouchableOpacity>
                    );
                  }
                )}
              </View>
            </>
          ) : (
            <>
              <TouchableOpacity
                style={
                  styles.dateRow
                }
              >
                <Ionicons
                  name="calendar-outline"
                  size={18}
                  color={
                    Colours.primary
                  }
                />

                <Text
                  style={
                    styles.dateText
                  }
                >
                  {date}
                </Text>

                <Ionicons
                name="chevron-forward"
                size={18}
                color="#9CA3AF"
                style={styles.chevron}
                />
              </TouchableOpacity>

              <TouchableOpacity
                style={
                  styles.dateRow
                }
              >
                <Ionicons
                  name="time-outline"
                  size={18}
                  color={
                    Colours.primary
                  }
                />

                <Text
                  style={
                    styles.dateText
                  }
                >
                  {time}
                </Text>
                <Ionicons
                name="chevron-forward"
                size={18}
                color="#9CA3AF"
                style={styles.chevron}
                />
              </TouchableOpacity>
            </>
          )}

          {/* Language */}

          <Text
            style={styles.section}
          >
            Language
          </Text>

          <View
            style={
              styles.chipRow
            }
          >
            {LANGUAGES.map(
              (
                item
              ) => {
                const selected =
                  item ===
                  localLanguage;

                return (
                  <TouchableOpacity
                    key={item}
                    style={[
                      styles.chip,
                      selected &&
                        styles.selectedChip,
                    ]}
                    onPress={() =>
                      setLocalLanguage(
                        item
                      )
                    }
                  >
                    <Text
                      style={[
                        styles.chipText,
                        selected &&
                          styles.selectedText,
                      ]}
                    >
                      {item}
                    </Text>
                  </TouchableOpacity>
                );
              }
            )}
          </View>

          <TouchableOpacity
            style={
              styles.applyButton
            }
            onPress={() => {
              onApply({
                openNow:
                  localOpenNow,

                accessible:
                  localAccessible,

                language:
                  localLanguage,

                autoCurrentTime,

                liveStatus,

                date,

                time,
              });

              onClose();
            }}
          >
            <Text
              style={
                styles.applyText
              }
            >
              Apply Filters
            </Text>
          </TouchableOpacity>

        </View>
      </View>
    </Modal>
  );
}

const styles =
  StyleSheet.create({
    overlay: {
      flex: 1,
      justifyContent:
        "flex-end",
      backgroundColor:
        "rgba(0,0,0,0.3)",
    },

    sheet: {
      backgroundColor:
        "#FFF",
      borderTopLeftRadius: 28,
      borderTopRightRadius: 28,
      padding: 24,
    },

    handle: {
      width: 50,
      height: 5,
      borderRadius: 3,
      backgroundColor:
        "#D1D5DB",
      alignSelf: "center",
      marginBottom: 20,
    },

    header: {
      flexDirection: "row",
      justifyContent:
        "space-between",
      alignItems: "center",
      marginBottom: 24,
    },

    title: {
      ...Typography.h2,
    },

    section: {
      fontWeight: "700",
      marginBottom: 12,
      marginTop: 12,
      color:
        Colours.text,
    },

    row: {
      flexDirection: "row",
      justifyContent:
        "space-between",
      alignItems: "center",
      marginBottom: 20,
    },

    label: {
      fontSize: 16,
      color:
        Colours.text,
    },

    chipRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      marginBottom: 20,
    },

    chip: {
      borderRadius: 999,
      backgroundColor:
        Colours.surface,
      paddingHorizontal: 16,
      paddingVertical: 10,
      marginRight: 10,
      marginBottom: 10,
    },

    selectedChip: {
      backgroundColor:
        Colours.primary,
    },

    chipText: {
      color:
        Colours.text,
      fontWeight: "600",
    },

    selectedText: {
      color: "#FFF",
    },

    dateRow: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor:
        Colours.surface,
      padding: 16,
      borderRadius: 12,
      marginBottom: 12,
    },

    dateText: {
      marginLeft: 12,
      color:
        Colours.text,
      fontSize: 16,
    },

    chevron: {
      marginLeft: "auto",
    },

    applyButton: {
      backgroundColor:
        Colours.primary,
      borderRadius: 16,
      paddingVertical: 16,
      alignItems: "center",
      marginTop: 10,
    },

    applyText: {
      color: "#FFF",
      fontSize: 16,
      fontWeight: "700",
    },
  });
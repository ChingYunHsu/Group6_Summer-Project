import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

import { mockMedicalId } from "../data/mockMedicalId";
import { mockProfile } from "../data/mockProfile";

type Scenario =
  | "allergies"
  | "respiratory"
  | "pain";

const phraseTemplates = {
  allergies: [
    {
      english:
        "I am having an allergic reaction.",
      translated:
        "Estoy teniendo una reacción alérgica.",
    },
    {
      english:
        "My throat is swelling up.",
      translated:
        "Se me está hinchando la garganta.",
    },
  ],

  respiratory: [
    {
      english:
        "My asthma is making it hard to breathe.",
      translated:
        "Mi asma me dificulta la respiración.",
    },
    {
      english:
        "I need my inhaler immediately.",
      translated:
        "Necesito mi inhalador inmediatamente.",
    },
  ],

  pain: [
    {
      english:
        "The pain is severe.",
      translated:
        "El dolor es intenso.",
    },
    {
      english:
        "The pain is an 8 out of 10.",
      translated:
        "El dolor es un 8 de 10.",
    },
  ],
};

export default function ShowStaffScreen() {
  const { t } = useTranslation(); 

  const [activeTab, setActiveTab] =
    useState<"phrases" | "translate">(
      "phrases"
    );

  const [scenario, setScenario] =
    useState<Scenario>("allergies");

  const [text, setText] =
    useState("");

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}

      <View style={styles.header}>
        <Text style={styles.title}>
  {t("showStaff.title")}
</Text>

        <TouchableOpacity
          onPress={() =>
            router.push("/profile")
          }
        >
          <View style={styles.avatar}>
            <Text
              style={
                styles.avatarInitials
              }
            >
              {
                mockProfile.avatar_initials
              }
            </Text>
          </View>
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={
          styles.content
        }
        showsVerticalScrollIndicator={
          false
        }
      >
        {/* Emergency Language Card */}

        <View style={styles.alertCard}>
          <View style={styles.alertBar} />

          <View
            style={styles.alertContent}
          >
            <Ionicons
              name="medical"
              size={28}
              color={Colours.danger}
            />

            <Text style={styles.languageBadge}>
  {t("showStaff.languageBadge")}
</Text>

            <Text
              style={styles.alertTitle}
            >
              {t("showStaff.visitorSpeaks")}{" "}
              <Text
                style={
                  styles.highlight
                }
              >
                {t("showStaff.language")}
              </Text>
              .
            </Text>

            <Text
              style={styles.alertTitle}
            >
              {t("showStaff.needAssistance")}
            </Text>

            <Text
              style={
                styles.translatedText
              }
            >
              {t("showStaff.translatedEmergency")}
            </Text>
          </View>
        </View>

        {/* Tabs */}

        <View style={styles.tabRow}>
          <TouchableOpacity
            style={[
              styles.tab,
              activeTab ===
                "phrases" &&
                styles.activeTab,
            ]}
            onPress={() =>
              setActiveTab(
                "phrases"
              )
            }
          >
            <Text
              style={[
                styles.tabText,
                activeTab ===
                  "phrases" &&
                  styles.activeTabText,
              ]}
            >
              {t("showStaff.commonPhrases")}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.tab,
              activeTab ===
                "translate" &&
                styles.activeTab,
            ]}
            onPress={() =>
              setActiveTab(
                "translate"
              )
            }
          >
            <Text
              style={[
                styles.tabText,
                activeTab ===
                  "translate" &&
                  styles.activeTabText,
              ]}
            >
              {t("showStaff.liveTranslate")}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Common Phrases */}

        {activeTab === "phrases" && (
          <>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={
                false
              }
              style={
                styles.chipContainer
              }
            >
              <ScenarioChip
                label={t("showStaff.allergies")}
                selected={
                  scenario ===
                  "allergies"
                }
                onPress={() =>
                  setScenario(
                    "allergies"
                  )
                }
              />

              <ScenarioChip
                label={t("showStaff.respiratory")}
                selected={
                  scenario ===
                  "respiratory"
                }
                onPress={() =>
                  setScenario(
                    "respiratory"
                  )
                }
              />

              <ScenarioChip
                label={t("showStaff.pain")}
                selected={
                  scenario ===
                  "pain"
                }
                onPress={() =>
                  setScenario(
                    "pain"
                  )
                }
              />
            </ScrollView>

            {phraseTemplates[
              scenario
            ].map(
              (
                phrase,
                index
              ) => (
                <View
                  key={index}
                  style={
                    styles.phraseCard
                  }
                >
                  <Text
                    style={
                      styles.englishText
                    }
                  >
                    {
                      phrase.english
                    }
                  </Text>

                  <Text
                    style={
                      styles.translatedPhrase
                    }
                  >
                    {
                      phrase.translated
                    }
                  </Text>
                </View>
              )
            )}
          </>
        )}

        {/* Live Translate */}

        {activeTab ===
          "translate" && (
          <View
            style={
              styles.translateCard
            }
          >
            <TextInput
              style={
                styles.translateInput
              }
              multiline
              placeholder={t("showStaff.translationPlaceholder")}
              value={text}
              onChangeText={setText}
            />

            <TouchableOpacity
              style={
                styles.micButton
              }
            >
              <Ionicons
                name="mic"
                size={22}
                color="#FFFFFF"
              />
            </TouchableOpacity>

            <Text
              style={
                styles.placeholderTranslation
              }
            >
              {t("showStaff.translationResult")}
            </Text>
          </View>
        )}

        {/* Medical Summary */}

        <View
          style={
            styles.medicalCard
          }
        >
          <Text style={styles.sectionTitle}>
  {t("showStaff.medicalSummary")}
</Text>

          <InfoRow
            label={t("profile.bloodType")}
            value={
              mockMedicalId.blood_type
            }
          />

          <InfoRow
            label={t("profile.conditions")}
            value={mockMedicalId.conditions.join(
              ", "
            )}
          />

          <InfoRow
            label={t("profile.allergies")}
            value={mockMedicalId.allergies.join(
              ", "
            )}
          />
        </View>
      </ScrollView>

      {/* SOS */}

      <TouchableOpacity
        style={styles.sosButton}
        onPress={() =>
          router.push("/sos")
        }
      >
        <Text style={styles.sosText}>
          SOS
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

function ScenarioChip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.chip,
        selected &&
          styles.selectedChip,
      ]}
      onPress={onPress}
    >
      <Text
        style={[
          styles.chipText,
          selected &&
            styles.selectedChipText,
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>
        {label}
      </Text>

      <Text style={styles.infoValue}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor:
      Colours.background,
  },

  header: {
    flexDirection: "row",
    justifyContent:
      "space-between",
    alignItems: "center",
    padding: 20,
  },

  title: {
    ...Typography.h1,
  },

  avatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor:
      Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
  },

  avatarInitials: {
    color: Colours.primary,
    fontWeight: "700",
  },

  content: {
    padding: 20,
    paddingBottom: 120,
  },

  alertCard: {
    backgroundColor:
      Colours.surface,
    borderRadius: 20,
    overflow: "hidden",
    flexDirection: "row",
    marginBottom: 20,
  },

  alertBar: {
    width: 6,
    backgroundColor:
      Colours.danger,
  },

  alertContent: {
    flex: 1,
    padding: 20,
  },

  languageBadge: {
    alignSelf: "flex-start",
    backgroundColor:
      Colours.surfaceLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    marginTop: 10,
    marginBottom: 12,
  },

  alertTitle: {
    fontSize: 28,
    fontWeight: "700",
    lineHeight: 36,
  },

  highlight: {
    color: Colours.primary,
  },

  translatedText: {
    marginTop: 12,
    color: Colours.muted,
    fontStyle: "italic",
  },

  tabRow: {
    flexDirection: "row",
    backgroundColor:
      Colours.surfaceLight,
    borderRadius: 12,
    padding: 4,
    marginBottom: 20,
  },

  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
  },

  activeTab: {
    backgroundColor:
      Colours.surface,
    borderRadius: 10,
  },

  tabText: {
    color: Colours.muted,
  },

  activeTabText: {
    color: Colours.primary,
    fontWeight: "700",
  },

  chipContainer: {
    marginBottom: 16,
  },

  chip: {
    backgroundColor:
      Colours.surface,
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginRight: 10,
  },

  selectedChip: {
    backgroundColor:
      Colours.primary,
  },

  chipText: {
    color: Colours.text,
  },

  selectedChipText: {
    color: "#FFFFFF",
  },

  phraseCard: {
    backgroundColor:
      Colours.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },

  englishText: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 6,
  },

  translatedPhrase: {
    color: Colours.muted,
    fontStyle: "italic",
  },

  translateCard: {
    backgroundColor:
      Colours.surface,
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },

  translateInput: {
    minHeight: 120,
    textAlignVertical: "top",
  },

  micButton: {
    alignSelf: "flex-end",
    backgroundColor:
      Colours.primary,
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 12,
  },

  placeholderTranslation: {
    marginTop: 16,
    color: Colours.muted,
  },

  medicalCard: {
    backgroundColor:
      Colours.surface,
    borderRadius: 16,
    padding: 16,
    marginTop: 10,
  },

  sectionTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 12,
  },

  infoRow: {
    marginBottom: 10,
  },

  infoLabel: {
    color: Colours.muted,
    fontSize: 12,
  },

  infoValue: {
    color: Colours.text,
  },

  sosButton: {
    position: "absolute",
    right: 24,
    bottom: 24,
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor:
      Colours.danger,
    justifyContent: "center",
    alignItems: "center",
    elevation: 5,
  },

  sosText: {
    color: "#FFFFFF",
    fontWeight: "800",
    fontSize: 18,
  },
});

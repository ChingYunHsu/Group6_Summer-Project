import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Brightness from "expo-brightness";
import * as Clipboard from "expo-clipboard";
import { router, useFocusEffect } from "expo-router";
import * as Speech from "expo-speech";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  AppState,
  AppStateStatus,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";
import {
  allergies as allergyList,
  getAllergyLabel,
} from "../../data/allergies";
import { featuredLanguages } from "../../data/languages";
import { getConditionLabel } from "../../data/medicalConditions";

import {
  phraseTemplates,
  Scenario,
  SupportedLanguage,
} from "../../data/phraseTemplates";
import { translateText } from "../../services/api";
import { getAccessToken } from "../../services/authService";
import { loadMedicalId } from "../../services/medicalIdService";
import { loadProfile } from "../../services/profileService";

type StaffSummary = {
  fullName?: string;
  phone?: string;
  bloodType?: string;
  conditions?: string;
  allergies?: string;
};

export default function ShowStaffScreen() {
  const { t } = useTranslation();

  const [currentLanguage, setCurrentLanguage] = useState(featuredLanguages[0]);

  const [summaryLoading, setSummaryLoading] = useState(true);
  const [staffSummary, setStaffSummary] = useState<StaffSummary | null>(null);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        const code = await AsyncStorage.getItem("language");

        const language =
          featuredLanguages.find((l) => l.code === code) ??
          featuredLanguages[0];

        setCurrentLanguage(language);
      })();
    }, []),
  );

  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          const token = await getAccessToken();

          if (!token) {
            setStaffSummary(null);
            return;
          }

          const [profile, medical] = await Promise.all([
            loadProfile().catch((error) => {
              console.error("Failed to load profile for staff summary", error);
              return null;
            }),
            loadMedicalId().catch((error) => {
              console.error(
                "Failed to load medical profile for staff summary",
                error,
              );
              return null;
            }),
          ]);

          if (!profile && !medical) {
            setStaffSummary(null);
            return;
          }

          // Always English here, regardless of the visitor's own app
          // language — this is what staff read. Free-text entries not
          // in the curated list pass through unchanged.
          setStaffSummary({
            fullName: profile?.full_name,
            phone: profile?.phone,
            bloodType: medical?.blood_type ?? undefined,
            conditions: medical?.conditions?.length
              ? medical.conditions
                  .map((item) => getConditionLabel(item, "en"))
                  .join(", ")
              : undefined,
            allergies: medical?.allergies?.length
              ? medical.allergies
                  .map((item) => getAllergyLabel(item, "en"))
                  .join(", ")
              : undefined,
          });
        } finally {
          setSummaryLoading(false);
        }
      })();
    }, []),
  );

  const selectedLanguage = currentLanguage.english as SupportedLanguage;
  const isTranslated = selectedLanguage !== "English";

  useEffect(() => {
    let previousBrightness: number | null = null;
    let isMounted = true;

    const maximizeBrightness = async () => {
      try {
        const current = await Brightness.getBrightnessAsync();
        if (!isMounted) return;
        if (previousBrightness === null) previousBrightness = current;
        await Brightness.setBrightnessAsync(1);
      } catch (error) {
        console.warn("Unable to adjust screen brightness", error);
      }
    };

    const restoreBrightness = () => {
      if (previousBrightness !== null) {
        Brightness.setBrightnessAsync(previousBrightness).catch(() => {});
      }
    };

    maximizeBrightness();

    const subscription = AppState.addEventListener(
      "change",
      (nextState: AppStateStatus) => {
        if (nextState === "active") {
          maximizeBrightness();
        } else {
          restoreBrightness();
        }
      },
    );

    return () => {
      isMounted = false;
      subscription.remove();
      restoreBrightness();
    };
  }, []);

  const [selectedScenario, setSelectedScenario] = useState<Scenario>("general");

  const [translationInput, setTranslationInput] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationFailed, setTranslationFailed] = useState(false);

  const [translationNeedsLogin, setTranslationNeedsLogin] = useState(false);

  const [translationRateLimited, setTranslationRateLimited] = useState(false);

  const translateStaffText = async (
    text: string,
    sourceLanguage: string,
  ): Promise<string> => {
    const result = await translateText(text, sourceLanguage, "en");
    return result.translatedText;
  };

  const trimmedInput = translationInput.trim();

  useEffect(() => {
    if (!trimmedInput) return;

    setIsTranslating(true);
    setTranslationFailed(false);
    setTranslationNeedsLogin(false);
    setTranslationRateLimited(false);

    const handle = setTimeout(async () => {
      try {
        const result = await translateStaffText(
          trimmedInput,
          currentLanguage.code,
        );
        setTranslatedText(result);
      } catch (error: any) {
        if (error?.status === 401) {
          setTranslationNeedsLogin(true);
        } else if (error?.status === 429) {
          setTranslationRateLimited(true);
        } else {
          setTranslationFailed(true);
        }
      } finally {
        setIsTranslating(false);
      }
    }, 1200);

    return () => clearTimeout(handle);
  }, [trimmedInput, currentLanguage.code]);

  const displayedTranslating = trimmedInput ? isTranslating : false;
  const displayedFailed = trimmedInput ? translationFailed : false;
  const displayedNeedsLogin = trimmedInput ? translationNeedsLogin : false;
  const displayedRateLimited = trimmedInput ? translationRateLimited : false;
  const displayedTranslation = trimmedInput ? translatedText : "";

  const categories: { key: Scenario; icon: keyof typeof Ionicons.glyphMap }[] =
    [
      { key: "general", icon: "chatbubble-outline" },
      { key: "emergency", icon: "warning-outline" },
      { key: "pain", icon: "fitness-outline" },
      { key: "allergies", icon: "flower-outline" },
      { key: "respiratory", icon: "medical-outline" },
      { key: "cardiac", icon: "heart-outline" },
      { key: "injury", icon: "bandage-outline" },
      { key: "hospital", icon: "business-outline" },
      { key: "pharmacy", icon: "medkit-outline" },
    ];

  const speakPhrase = (text: string, language: SupportedLanguage) => {
    const languageMap: Record<SupportedLanguage, string> = {
      English: "en-US",
      Spanish: "es-ES",
      French: "fr-FR",
      Italian: "it-IT",
      German: "de-DE",
      Chinese: "zh-CN",
    };

    Speech.stop();

    Speech.speak(text, {
      language: languageMap[language],
    });
  };

  const copyPhrase = async (text: string) => {
    await Clipboard.setStringAsync(text);
  };

  const handleCancel = () => {
    router.back();
  };

  const heroPhrase = phraseTemplates.general[0];

  const visiblePhrases =
    selectedScenario === "general"
      ? phraseTemplates.general.filter((phrase) => phrase !== heroPhrase)
      : phraseTemplates[selectedScenario];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <TouchableOpacity style={styles.closeButton} onPress={handleCancel}>
          <Ionicons name="close" size={28} color={Colours.text} />
        </TouchableOpacity>

        <Text style={styles.title}>{t("showStaff.title")}</Text>

        <View style={styles.heroCard}>
          <View style={styles.languageBadge}>
            <Text style={styles.languageBadgeText}>
              {currentLanguage.flag} {currentLanguage.english} /{" "}
              {currentLanguage.native}
            </Text>
          </View>

          <Text style={styles.heroTitle}>
            {t("showStaff.visitorSpeaks", { lng: "en" })}
          </Text>

          <Text style={styles.languageText}>{currentLanguage.english}</Text>

          <View style={styles.staffPhraseRow}>
            <Text style={styles.staffPhraseText}>{heroPhrase.english}</Text>

            <TouchableOpacity
              onPress={() => speakPhrase(heroPhrase.english, "English")}
            >
              <Ionicons name="volume-high" size={26} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          {isTranslated && (
            <View style={styles.translationBox}>
              <Text style={styles.nativeReferenceText}>
                {heroPhrase.translations[selectedLanguage]}
              </Text>
            </View>
          )}
        </View>

        <Text style={styles.sectionTitle}>{t("showStaff.commonPhrases")}</Text>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.categoryContainer}
        >
          {categories.map((category) => {
            const selected = selectedScenario === category.key;

            return (
              <TouchableOpacity
                key={category.key}
                style={[
                  styles.categoryChip,
                  selected && styles.categoryChipSelected,
                ]}
                onPress={() => setSelectedScenario(category.key)}
              >
                <Ionicons
                  name={category.icon}
                  size={18}
                  color={selected ? "#FFF" : Colours.primary}
                />

                <Text
                  style={[
                    styles.categoryText,
                    selected && styles.categoryTextSelected,
                  ]}
                >
                  {t(`showStaff.categories.${category.key}`)}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {visiblePhrases.map((phrase) => (
          <View key={phrase.english} style={styles.phraseCard}>
            <Text style={styles.staffPhraseText}>{phrase.english}</Text>

            {isTranslated && (
              <Text style={styles.nativeReferenceCaption}>
                {phrase.translations[selectedLanguage]}
              </Text>
            )}

            <View style={styles.actions}>
              <TouchableOpacity onPress={() => copyPhrase(phrase.english)}>
                <Ionicons
                  name="copy-outline"
                  size={22}
                  color={Colours.primary}
                />
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => speakPhrase(phrase.english, "English")}
              >
                <Ionicons
                  name="volume-high-outline"
                  size={22}
                  color={Colours.primary}
                />
              </TouchableOpacity>
            </View>
          </View>
        ))}

        <Text style={styles.sectionTitle}>{t("showStaff.liveTranslate")}</Text>

        <TextInput
          value={translationInput}
          onChangeText={setTranslationInput}
          placeholder={t("showStaff.translationPlaceholder")}
          placeholderTextColor={Colours.muted}
          multiline
          style={styles.input}
        />

        <View style={styles.translationResult}>
          {displayedTranslating ? (
            <ActivityIndicator color={Colours.primary} />
          ) : displayedNeedsLogin ? (
            <TouchableOpacity onPress={() => router.push("/login")}>
              <Text style={styles.translationErrorText}>
                {t("showStaff.translationLoginRequired", {
                  defaultValue: "Log in to use Live Translate. Tap to log in.",
                })}
              </Text>
            </TouchableOpacity>
          ) : displayedRateLimited ? (
            <Text style={styles.translationErrorText}>
              {t("showStaff.translationRateLimited", {
                defaultValue:
                  "Too many translations at once — please wait a moment and try again.",
              })}
            </Text>
          ) : displayedFailed ? (
            <Text style={styles.translationErrorText}>
              {t("showStaff.translationError", {
                defaultValue: "Translation failed. Please try again.",
              })}
            </Text>
          ) : (
            <Text style={styles.translationResultText}>
              {displayedTranslation || t("showStaff.translationResult")}
            </Text>
          )}
        </View>

        {/* Medical summary card — labels forced to English (lng: "en"),
            matching the already-English condition/allergy values, since
            this is the card most likely to be read directly by
            English-speaking staff. */}
        {summaryLoading ? (
          <>
            <Text style={styles.sectionTitle}>
              {t("showStaff.medicalSummary")}
            </Text>
            <View style={styles.summaryCard}>
              <ActivityIndicator color={Colours.primary} />
            </View>
          </>
        ) : (
          staffSummary && (
            <>
              <Text style={styles.sectionTitle}>
                {t("showStaff.medicalSummary")}
              </Text>

              <View style={styles.summaryCard}>
                <InfoRow
                  label={t("profile.fullName", { lng: "en" })}
                  value={staffSummary.fullName}
                />

                <InfoRow
                  label={t("profile.bloodType", { lng: "en" })}
                  value={staffSummary.bloodType}
                />

                <InfoRow
                  label={t("profile.conditions", { lng: "en" })}
                  value={staffSummary.conditions}
                />

                <InfoRow
                  label={t("profile.allergies", { lng: "en" })}
                  value={staffSummary.allergies}
                />

                <InfoRow
                  label={t("profile.phone", { lng: "en" })}
                  value={staffSummary.phone}
                />
              </View>
            </>
          )
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

type InfoRowProps = { label: string; value?: string | null };

function InfoRow({ label, value }: InfoRowProps) {
  if (!value) return null;

  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colours.background },

  content: { padding: 20, paddingBottom: 40 },

  closeButton: { alignSelf: "flex-start", marginBottom: 12 },

  title: { ...Typography.h2, color: Colours.text, marginBottom: 20 },

  heroCard: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 20,
    padding: 20,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colours.borderLight,
  },

  languageBadge: {
    alignSelf: "flex-start",
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 16,
  },

  languageBadgeText: { color: "#FFF", fontWeight: "700", fontSize: 13 },

  heroTitle: { ...Typography.bodySmall, color: Colours.muted, marginBottom: 6 },

  languageText: { ...Typography.h2, color: Colours.text, marginBottom: 16 },

  staffPhraseRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
  },

  staffPhraseText: {
    flexShrink: 1,
    fontSize: 32,
    lineHeight: 40,
    fontWeight: "700",
    color: Colours.text,
  },

  nativeReferenceText: {
    fontSize: 18,
    lineHeight: 24,
    color: Colours.muted,
  },

  nativeReferenceCaption: {
    fontSize: 16,
    color: Colours.muted,
    marginTop: 10,
  },

  translationBox: {
    backgroundColor: Colours.surface,
    borderRadius: 14,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  sectionTitle: {
    ...Typography.h3,
    color: Colours.text,
    marginBottom: 14,
    marginTop: 8,
  },

  categoryContainer: { paddingBottom: 10, paddingRight: 20 },

  categoryChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surfaceLight,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999,
    marginRight: 10,
    borderWidth: 1,
    borderColor: Colours.border,
    gap: 8,
  },

  categoryChipSelected: {
    backgroundColor: Colours.primary,
    borderColor: Colours.primary,
  },

  categoryText: { color: Colours.text, fontWeight: "600" },

  categoryTextSelected: { color: "#FFF" },

  phraseCard: {
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  actions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 18,
    gap: 18,
  },

  input: {
    backgroundColor: Colours.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    padding: 16,
    minHeight: 140,
    fontSize: 32,
    lineHeight: 40,
    color: Colours.text,
    textAlignVertical: "top",
    marginBottom: 16,
  },

  translationResult: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    padding: 18,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colours.borderLight,
  },

  translationResultText: {
    fontSize: 32,
    lineHeight: 40,
    color: Colours.muted,
  },

  translationErrorText: {
    fontSize: 20,
    color: "#D32F2F",
    fontWeight: "600",
  },

  summaryCard: {
    backgroundColor: Colours.surface,
    borderRadius: 20,
    padding: 18,
    marginBottom: 30,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  infoRow: { marginBottom: 18 },

  infoLabel: { ...Typography.caption, color: Colours.muted, marginBottom: 4 },

  infoValue: {
    fontSize: 32,
    lineHeight: 40,
    color: Colours.text,
    fontWeight: "600",
  },
});

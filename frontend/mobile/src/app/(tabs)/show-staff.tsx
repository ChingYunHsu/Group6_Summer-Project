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
import { featuredLanguages } from "../../data/languages";

import {
  phraseTemplates,
  Scenario,
  SupportedLanguage,
} from "../../data/phraseTemplates";
import { translateText } from "../../services/api";
import { getAccessToken } from "../../services/authService";
import { loadMedicalId } from "../../services/medicalIdService";
import { loadProfile } from "../../services/profileService";

// The medical summary card below fetches real data from
// GET /api/v1/user/medical-profile (and /user/profile for name/phone) —
// no more mock imports.

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

  // useFocusEffect, not plain useEffect — currentLanguage here represents
  // the app user's own chosen language ("I am the visitor, and I speak
  // whatever I've set my app to"), so it should track changes made
  // anywhere else in the app. A mount-only effect meant this tab, once
  // visited, would never see a language change made after that — Expo
  // Router keeps tab screens mounted rather than remounting them, so
  // "load once on mount" really meant "load once, ever, per app session."
  // Same fix already applied to profile.tsx/settings.tsx earlier.
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

  // Full name/phone live on the profile resource, blood type/conditions/
  // allergies live on the medical resource — two separate backend calls,
  // same pattern as edit-profile.tsx. If there's no token at all, there's
  // no personal data to show, so we skip both calls entirely rather than
  // firing requests that would just 401.
  useEffect(() => {
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

        setStaffSummary({
          fullName: profile?.full_name,
          phone: profile?.phone,
          bloodType: medical?.blood_type ?? undefined,
          conditions: medical?.conditions?.length
            ? medical.conditions.join(", ")
            : undefined,
          allergies: medical?.allergies?.length
            ? medical.allergies.join(", ")
            : undefined,
        });
      } finally {
        setSummaryLoading(false);
      }
    })();
  }, []);

  // This screen is read by Manhattan-based staff, who read English — so the
  // *phrase content* shown large is always English, regardless of the
  // visitor's language. `selectedLanguage` is only used to pull the
  // visitor's own native-language text for the smaller reference captions
  // (so the visitor can confirm the phrase says what they mean) and for
  // text-to-speech.
  const selectedLanguage = currentLanguage.english as SupportedLanguage;
  const isTranslated = selectedLanguage !== "English";

  useEffect(() => {
    // On iOS, a brightness override set via setBrightnessAsync persists
    // until the device is locked — it does NOT automatically revert just
    // because the user backgrounds the app (e.g. to take a call). So we
    // can't rely on unmount alone to satisfy "restore on exit"; we also
    // watch AppState and restore/re-max as the app backgrounds/foregrounds
    // while this screen is still on top.
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

  // Distinct from translationFailed — /translate requires a real login
  // server-side (require_bearer_auth, confirmed via
  // test_translate_requires_bearer_token in the backend test suite), and
  // a guest hitting that should see "log in to use this" rather than a
  // generic failure message that gives no indication of what would
  // actually fix it. This screen is exactly the one an unregistered
  // traveler might reach for first, so this distinction matters here
  // more than most other auth-gated features.
  const [translationNeedsLogin, setTranslationNeedsLogin] = useState(false);

  // Translate free text server-side, not on-device — arbitrary visitor
  // input isn't covered by the canned phraseTemplates, and running this
  // through a third-party provider directly from the client would mean
  // shipping an API key in the app bundle. Wired to POST /api/v1/translate
  // (Gemini-backed, backend/src/api/translate.py) — on failure this
  // throws rather than falling back to anything, since the callers below
  // treat a thrown error as "show the failure state", and a fabricated
  // medical translation would be worse than an obvious failure.
  const translateStaffText = async (
    text: string,
    sourceLanguage: string,
  ): Promise<string> => {
    const result = await translateText(text, sourceLanguage, "en");
    return result.translatedText;
  };

  // The trimmed value is what actually drives the debounce/translate
  // effect below. Computing it here (render time) means the "nothing to
  // translate" case can be handled by the derived `displayed*` values
  // below, rather than by resetting state imperatively in the effect.
  const trimmedInput = translationInput.trim();

  // Debounced so we don't fire a request on every keystroke — waits for a
  // pause in typing before translating. This is a legitimate "synchronize
  // with an external/async process" effect; the lint rule flags the
  // setIsTranslating(true) call anyway since it's synchronous at the top
  // of the effect, so it's disabled here rather than restructured further.
  useEffect(() => {
    if (!trimmedInput) return;

    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: marks the debounced translation as starting
    setIsTranslating(true);
    setTranslationFailed(false);
    setTranslationNeedsLogin(false);

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
        } else {
          setTranslationFailed(true);
        }
      } finally {
        setIsTranslating(false);
      }
    }, 500);

    return () => clearTimeout(handle);
  }, [trimmedInput, currentLanguage.code]);

  // When the input is empty there's nothing to show/translate, regardless
  // of whatever the last non-empty translation attempt left in state.
  const displayedTranslating = trimmedInput ? isTranslating : false;
  const displayedFailed = trimmedInput ? translationFailed : false;
  const displayedNeedsLogin = trimmedInput ? translationNeedsLogin : false;
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

  // The General category's first phrase is always the hero phrase above
  // — showing it a second time in the card list right underneath looked
  // redundant. Only relevant for "general"; other categories don't
  // contain this phrase at all, so nothing to filter there.
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
        {/* Header */}

        <TouchableOpacity style={styles.closeButton} onPress={handleCancel}>
          <Ionicons name="close" size={28} color={Colours.text} />
        </TouchableOpacity>

        <Text style={styles.title}>{t("showStaff.title")}</Text>

        {/* Language Card */}

        <View style={styles.heroCard}>
          <View style={styles.languageBadge}>
            <Text style={styles.languageBadgeText}>
              {currentLanguage.flag} {currentLanguage.english} /{" "}
              {currentLanguage.native}
            </Text>
          </View>

          {/* This caption is context FOR STAFF ("this patient speaks X"),
              not navigation for the visitor — unlike the section headers
              below (Common Phrases, Live Translate, etc.), which stay in
              the visitor's language since the visitor uses those to
              operate the app. Forced to English via the i18next `lng`
              override so it still comes from the shared translation
              files rather than being hardcoded here. */}
          <Text style={styles.heroTitle}>
            {t("showStaff.visitorSpeaks", { lng: "en" })}
          </Text>

          <Text style={styles.languageText}>{currentLanguage.english}</Text>

          {/* Primary content: always English, for staff to read. The
              speaker icon lives right next to it now, since this is the
              text it actually plays. */}
          <View style={styles.staffPhraseRow}>
            <Text style={styles.staffPhraseText}>{heroPhrase.english}</Text>

            <TouchableOpacity
              onPress={() => speakPhrase(heroPhrase.english, "English")}
            >
              <Ionicons name="volume-high" size={26} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          {/* Secondary reference: visitor's own language, so they can
              confirm the phrase means what they intend before showing it.
              Plain text only — no speaker icon here, since audio always
              plays the English version above, not this. */}
          {isTranslated && (
            <View style={styles.translationBox}>
              <Text style={styles.nativeReferenceText}>
                {heroPhrase.translations[selectedLanguage]}
              </Text>
            </View>
          )}
        </View>

        {/* Categories */}

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

        {/* Phrase Cards */}

        {visiblePhrases.map((phrase) => (
          <View key={phrase.english} style={styles.phraseCard}>
            {/* Primary content: always English, for staff to read */}
            <Text style={styles.staffPhraseText}>{phrase.english}</Text>

            {/* Secondary reference: visitor's own language */}
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

        {/* Live Translate */}

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

        {/* Medical ID — omitted entirely (not shown empty/broken) if the
            person isn't logged in or the fetch failed. See the note about
            the medical-profile shadow-routing bug at the top of this
            file. */}

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
                  label={t("profile.fullName")}
                  value={staffSummary.fullName}
                />

                <InfoRow
                  label={t("profile.bloodType")}
                  value={staffSummary.bloodType}
                />

                <InfoRow
                  label={t("profile.conditions")}
                  value={staffSummary.conditions}
                />

                <InfoRow
                  label={t("profile.allergies")}
                  value={staffSummary.allergies}
                />

                <InfoRow
                  label={t("profile.phone")}
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
  // Per spec: missing or null fields are omitted entirely, never shown
  // with a placeholder like "Not provided".
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

  // Primary, staff-facing communication content. Mockup spec requires a minimum
  // of 32px here — hard-coded rather than relying on Typography.h3 in case
  // that token is ever tuned below 32px elsewhere in the app. Consider
  // hoisting this into constants/typography.ts as e.g. `Typography.staffDisplay`
  // if other accessibility screens (medical-id, sos) need the same treatment.
  staffPhraseText: {
    flexShrink: 1,
    fontSize: 32,
    lineHeight: 40,
    fontWeight: "700",
    color: Colours.text,
  },

  // Secondary reference text (visitor's own language) — intentionally
  // smaller since it's a confirmation aid, not the primary communicated
  // content read by staff.
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

  // Hard-coded since `Colours` doesn't currently define an error/danger
  // token — worth adding one (e.g. Colours.danger) if error states appear
  // elsewhere in the app too.
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

  // Visit summary content — spec requires 32px minimum.
  infoValue: {
    fontSize: 32,
    lineHeight: 40,
    color: Colours.text,
    fontWeight: "600",
  },
});

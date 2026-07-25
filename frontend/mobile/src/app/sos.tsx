import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { getAllergyLabel } from "../data/allergies";
import { getConditionLabel } from "../data/medicalConditions";
import { getAccessToken } from "../services/authService";
import {
  getCurrentLocation,
  requestLocationPermission,
} from "../services/location";
import { loadMedicalId, MedicalProfile } from "../services/medicalIdService";
import { loadProfile, UserProfile } from "../services/profileService";

export default function SOSScreen() {
  const [countdown, setCountdown] = useState(5);

  const { t } = useTranslation();

  // DEMO MODE — set to true before shipping/submitting the real build.
  // Prevents SOSScreen from placing an actual emergency call during
  // presentations/testing while leaving the full flow intact to demo.
  const ENABLE_REAL_EMERGENCY_CALL = false;

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [medicalId, setMedicalId] = useState<MedicalProfile | null>(null);

  const [locationText, setLocationText] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();

        if (!token) {
          return;
        }

        const [profileResult, medicalResult] = await Promise.all([
          loadProfile().catch((error) => {
            console.error("Failed to load profile for SOS", error);
            return null;
          }),
          loadMedicalId().catch((error) => {
            console.error("Failed to load medical ID for SOS", error);
            return null;
          }),
        ]);

        setProfile(profileResult);
        setMedicalId(medicalResult);
      } catch (error) {
        console.error("Failed to load SOS medical summary", error);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const servicesEnabled = await Location.hasServicesEnabledAsync();

        if (!servicesEnabled) {
          return;
        }

        const granted = await requestLocationPermission();

        if (!granted) {
          return;
        }

        const position = await getCurrentLocation();

        if (!position) {
          return;
        }

        const results = await Location.reverseGeocodeAsync({
          latitude: position.latitude,
          longitude: position.longitude,
        });

        const address = results[0];

        if (!address) {
          return;
        }

        const parts = [
          [address.streetNumber, address.street].filter(Boolean).join(" "),
          address.city,
          [address.region, address.postalCode].filter(Boolean).join(" "),
        ].filter(Boolean);

        setLocationText(parts.join(", "));
      } catch (error) {
        console.error("Failed to resolve SOS location", error);
      }
    })();
  }, []);

  const handleCallEmergency = async () => {
    const phoneNumber = "911";
    const url = `tel:${phoneNumber}`;

    const supported = await Linking.canOpenURL(url);

    if (!supported) {
      Alert.alert(t("sos.callErrorTitle"), t("sos.callErrorMessage"));
      return;
    }

    if (!ENABLE_REAL_EMERGENCY_CALL) {
      console.log(
        "DEMO MODE: would dial",
        phoneNumber,
        "— real call suppressed",
      );
      Alert.alert(
        t("sos.demoModeTitle"),
        t("sos.demoModeMessage", { phoneNumber }),
      );
      return;
    }

    await Linking.openURL(url);
  };

  useEffect(() => {
    if (countdown === 0) {
      handleCallEmergency();
      return;
    }

    const timer = setTimeout(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [countdown]);

  const handleCancel = () => {
    router.back();
  };

  // Conditions/allergies values are always shown in English on this
  // screen, regardless of the app's own language setting — matched by
  // the medical card's labels below, all forced to lng: "en". The rest
  // of this screen (countdown, cancel, notice) still follows the app's
  // normal active language. Free-text entries not in the curated list
  // pass through unchanged.
  const conditionsText = medicalId?.conditions?.length
    ? medicalId.conditions
        .map((item) => getConditionLabel(item, "en"))
        .join(", ")
    : null;

  const allergiesText = medicalId?.allergies?.length
    ? medicalId.allergies.map((item) => getAllergyLabel(item, "en")).join(", ")
    : null;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <TouchableOpacity
          testID="sos-close-button"
          style={styles.closeButton}
          onPress={handleCancel}
        >
          <Ionicons name="close" size={28} color="#FFFFFF" />
        </TouchableOpacity>

        <View style={styles.hero}>
          <Ionicons name="warning" size={64} color="#FFFFFF" />

          <Text style={styles.sosTitle}>{t("sos.title")}</Text>

          <Text style={styles.timer}>
            {t("sos.countdown", { seconds: countdown })}
          </Text>

          <Text style={styles.subtitle}>{t("sos.subtitle")}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{t("sos.locationTitle")}</Text>

          <Text style={styles.cardText}>
            {locationText ??
              t("sos.locationUnavailable", {
                defaultValue: "Unable to determine your current location.",
              })}
          </Text>

          <Text style={styles.cardSubtext}>{t("sos.locationDescription")}</Text>
        </View>

        {/* Medical ID card — every label below is forced to English
            (lng: "en"), matching the already-English condition/allergy
            values, since this card is the one most likely to be read
            directly by an English-speaking responder. */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>
            {t("sos.medicalIdTitle", { lng: "en" })}
          </Text>

          <InfoRow
            label={t("sos.name", { lng: "en" })}
            value={profile?.full_name ?? null}
          />

          <InfoRow
            label={t("sos.bloodType", { lng: "en" })}
            value={medicalId?.blood_type ?? null}
          />

          <InfoRow
            label={t("sos.conditions", { lng: "en" })}
            value={
              medicalId === null
                ? null
                : (conditionsText ?? t("sos.none", { lng: "en" }))
            }
          />

          <InfoRow
            label={t("sos.allergies", { lng: "en" })}
            value={
              medicalId === null
                ? null
                : (allergiesText ?? t("sos.none", { lng: "en" }))
            }
          />

          <InfoRow
            label={t("sos.phone", { lng: "en" })}
            value={profile?.phone ?? null}
          />
        </View>

        <View style={styles.notice}>
          <Ionicons name="information-circle" size={20} color="#FFFFFF" />

          <Text style={styles.noticeText}>{t("sos.notice")}</Text>
        </View>

        <TouchableOpacity
          testID="sos-cancel-button"
          style={styles.cancelButton}
          onPress={handleCancel}
        >
          <Text style={styles.cancelText}>{t("sos.cancel")}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

type InfoRowProps = {
  label: string;
  value: string | null;
};

// Used only inside the medical ID card, so its own "Not provided"
// fallback is forced to English too, for the same reason as the labels
// around it.
function InfoRow({ label, value }: InfoRowProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>

      <Text style={styles.infoValue}>
        {value ?? t("sos.notProvided", { lng: "en" })}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#C62828",
  },

  closeButton: {
    position: "absolute",
    top: 12,
    left: 12,
    zIndex: 10,
  },

  hero: {
    alignItems: "center",
    marginTop: 20,
    marginBottom: 30,
  },

  sosTitle: {
    fontSize: 34,
    fontWeight: "800",
    color: "#FFFFFF",
    marginTop: 12,
    textAlign: "center",
  },

  timer: {
    fontSize: 42,
    fontWeight: "800",
    color: "#FFFFFF",
    marginTop: 10,
  },

  subtitle: {
    color: "#FFFFFF",
    textAlign: "center",
    marginTop: 12,
    opacity: 0.9,
    fontSize: 16,
    lineHeight: 22,
  },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
  },

  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 12,
  },

  cardText: {
    color: Colours.text,
    marginBottom: 6,
  },

  cardSubtext: {
    color: Colours.muted,
    fontSize: 12,
    lineHeight: 18,
  },

  infoRow: {
    marginBottom: 12,
  },

  infoLabel: {
    fontSize: 12,
    color: Colours.muted,
    marginBottom: 2,
  },

  infoValue: {
    color: Colours.text,
    fontSize: 15,
  },

  notice: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
    marginBottom: 20,
  },

  noticeText: {
    color: "#FFFFFF",
    marginLeft: 10,
    flex: 1,
    lineHeight: 20,
  },

  cancelButton: {
    backgroundColor: "#FFFFFF",
    borderRadius: 999,
    paddingVertical: 18,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 12,
  },

  cancelText: {
    color: "#C62828",
    fontWeight: "800",
    fontSize: 16,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 32,
  },
});

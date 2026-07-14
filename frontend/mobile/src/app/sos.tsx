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

  // null = not logged in / fetch failed / never resolved — InfoRow shows
  // "Not provided" in that case. Distinct from an empty conditions/
  // allergies array, which shows "None" instead — "we confirmed there
  // are none" and "we don't know" are clinically different things to
  // show a first responder, not interchangeable blanks.
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [medicalId, setMedicalId] = useState<MedicalProfile | null>(null);

  const [locationText, setLocationText] = useState<string | null>(null);

  // Fetches profile + medical data for the summary card below. Fully
  // independent of the countdown/auto-dial logic further down — this
  // must never be able to delay or block the actual emergency call, so
  // nothing here is awaited by handleCallEmergency or the countdown
  // effect.
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

  // Real device location, reverse-geocoded into a readable address —
  // replaces the previous hardcoded "245 W 46th St..." placeholder.
  // Same independence guarantee as above: never gates the emergency call
  // itself, only what's displayed for the person's own reference.
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
    // Replace with region-specific emergency number if the app expands outside the US

    const supported = await Linking.canOpenURL(url);

    if (!supported) {
      Alert.alert(t("sos.callErrorTitle"), t("sos.callErrorMessage"));
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

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Close */}

        <TouchableOpacity style={styles.closeButton} onPress={handleCancel}>
          <Ionicons name="close" size={28} color="#FFFFFF" />
        </TouchableOpacity>

        {/* Hero */}

        <View style={styles.hero}>
          <Ionicons name="warning" size={64} color="#FFFFFF" />

          <Text style={styles.sosTitle}>{t("sos.title")}</Text>

          <Text style={styles.timer}>
            {t("sos.countdown", { seconds: countdown })}
          </Text>

          <Text style={styles.subtitle}>{t("sos.subtitle")}</Text>
        </View>

        {/* Location */}

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

        {/* Medical ID */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>{t("sos.medicalIdTitle")}</Text>

          <InfoRow label={t("sos.name")} value={profile?.full_name ?? null} />

          <InfoRow
            label={t("sos.bloodType")}
            value={medicalId?.blood_type ?? null}
          />

          <InfoRow
            label={t("sos.conditions")}
            value={
              medicalId === null
                ? null
                : medicalId.conditions?.length
                  ? medicalId.conditions.join(", ")
                  : t("sos.none")
            }
          />

          <InfoRow
            label={t("sos.allergies")}
            value={
              medicalId === null
                ? null
                : medicalId.allergies?.length
                  ? medicalId.allergies.join(", ")
                  : t("sos.none")
            }
          />

          <InfoRow label={t("sos.phone")} value={profile?.phone ?? null} />
        </View>

        {/* Emergency Notice */}

        <View style={styles.notice}>
          <Ionicons name="information-circle" size={20} color="#FFFFFF" />

          <Text style={styles.noticeText}>{t("sos.notice")}</Text>
        </View>

        {/* Cancel */}

        <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
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

function InfoRow({ label, value }: InfoRowProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>

      <Text style={styles.infoValue}>{value ?? t("sos.notProvided")}</Text>
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

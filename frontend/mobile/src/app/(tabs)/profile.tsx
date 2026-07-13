import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../../constants/colours";
import { Typography } from "../../constants/typography";
import { mockProfile } from "../../data/mockProfile";
import {
  DEFAULT_MEDICAL_PROFILE,
  loadMedicalId,
  MedicalProfile,
} from "../../services/medicalIdService";
import { loadProfile } from "../../services/profileService";

export default function ProfileScreen() {
  const [loading, setLoading] = useState(true);

  // Tracked separately per resource (profile vs. medical), since they're
  // two independent fetches — "synced" only if both succeeded, "offline"
  // if either failed. Previously a single syncStatus only ever reflected
  // the profile fetch; a failed medical fetch had no visible signal at
  // all.
  const [profileSyncOk, setProfileSyncOk] = useState<boolean | null>(null);
  const [medicalSyncOk, setMedicalSyncOk] = useState<boolean | null>(null);

  const syncStatus: "loading" | "synced" | "offline" =
    profileSyncOk === null || medicalSyncOk === null
      ? "loading"
      : profileSyncOk && medicalSyncOk
        ? "synced"
        : "offline";

  const { t } = useTranslation();

  const [profile, setProfile] = useState(mockProfile);

  // mockMedicalId is no longer a valid seed here — see the comment on
  // DEFAULT_MEDICAL_PROFILE in medicalIdService.ts for why.
  const [medicalId, setMedicalId] = useState<MedicalProfile>(
    DEFAULT_MEDICAL_PROFILE,
  );

  const handleScanQR = () => {
    Alert.alert(t("profile.scanQr"), t("profile.scanQrMessage"));
  };

  useEffect(() => {
    async function getProfile() {
      try {
        const savedProfile = await loadProfile();

        if (savedProfile) {
          setProfile(savedProfile);
        }

        setProfileSyncOk(true);
      } catch (error) {
        console.error(error);
        setProfileSyncOk(false);
      } finally {
        setLoading(false);
      }
    }

    getProfile();
  }, []);

  useEffect(() => {
    async function getMedicalId() {
      try {
        const savedMedicalId = await loadMedicalId();

        if (savedMedicalId) {
          setMedicalId(savedMedicalId);
        }

        setMedicalSyncOk(true);
      } catch (error) {
        console.error("Failed to load medical ID", error);
        setMedicalSyncOk(false);
      }
    }

    getMedicalId();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}

        <Text style={styles.title}>{t("profile.title")}</Text>

        {/* Profile Summary */}

        <View style={styles.profileHeader}>
          <View style={styles.avatar}>
            <Text style={styles.avatarInitials}>{profile.avatar_initials}</Text>
          </View>

          <Text style={styles.profileName}>{profile.full_name}</Text>

          <Text style={styles.profileEmail}>{profile.email}</Text>
        </View>

        {/* Sync Status — now actually reflects syncStatus instead of
            always showing a hardcoded "Synced" regardless of what
            happened. */}

        <View style={styles.syncCard}>
          {syncStatus === "loading" ? (
            <ActivityIndicator size="small" color={Colours.primary} />
          ) : (
            <Ionicons
              name={syncStatus === "synced" ? "cloud-done" : "cloud-offline"}
              size={22}
              color={
                syncStatus === "offline" ? Colours.danger : Colours.primary
              }
            />
          )}

          <View style={styles.syncContent}>
            <Text style={styles.syncTitle}>
              {syncStatus === "synced"
                ? t("profile.synced")
                : syncStatus === "offline"
                  ? t("profile.syncOffline", {
                      defaultValue: "Offline — showing saved data",
                    })
                  : t("profile.syncLoading", { defaultValue: "Syncing…" })}
            </Text>

            <Text style={styles.syncText}>{t("profile.lastUpdated")}</Text>
          </View>
        </View>

        {/* Personal Information */}

        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>
              {t("editProfile.personalInformation")}
            </Text>

            <TouchableOpacity onPress={() => router.push("/edit-profile")}>
              <Text style={styles.editText}>{t("common.edit")}</Text>
            </TouchableOpacity>
          </View>

          {/* user_id and email: no endpoint currently returns either for
              the logged-in user (get_user_profile's SELECT doesn't
              include them) — these two rows are unavoidably still mock
              until that's added server-side. Everything else below is
              live. */}

          <InfoRow label={t("profile.userId")} value={profile.user_id} />

          <InfoRow label={t("profile.fullName")} value={profile.full_name} />

          <InfoRow label={t("profile.email")} value={profile.email} />

          <InfoRow label={t("profile.phone")} value={profile.phone} />

          {/* date_of_birth/gender/address live on the medical-profile
              resource, not /user/profile — sourced from medicalId, not
              profile, to actually be live. */}

          <InfoRow
            label={t("profile.dateOfBirth")}
            value={medicalId.date_of_birth ?? ""}
          />

          <InfoRow label={t("profile.gender")} value={medicalId.gender ?? ""} />

          <InfoRow
            label={t("profile.nationality")}
            value={profile.nationality}
          />

          <InfoRow
            label={t("profile.languages")}
            value={(profile.spoken_languages ?? []).join(", ")}
          />

          <InfoRow
            label={t("profile.address")}
            value={medicalId.address ?? ""}
          />
        </View>

        {/* Medical ID */}

        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t("profile.medicalId")}</Text>

            <TouchableOpacity onPress={() => router.push("/medical-id")}>
              <Text style={styles.editText}>{t("common.edit")}</Text>
            </TouchableOpacity>
          </View>

          <InfoRow
            label={t("profile.bloodType")}
            value={medicalId.blood_type ?? ""}
          />

          <InfoRow
            label={t("profile.conditions")}
            value={(medicalId.conditions ?? []).join(", ")}
          />

          <InfoRow
            label={t("profile.allergies")}
            value={(medicalId.allergies ?? []).join(", ")}
          />
        </View>

        {/* Saved Clinics — still static placeholder content (St. Mary's /
            CityMD are literal strings, not from /user/favourites or
            matching any real seeded venue). Left as-is on purpose:
            favourites hasn't been incorporated client-side yet. */}

        <Text style={styles.savedTitle}>{t("profile.savedClinics")}</Text>

        <View style={styles.clinicCard}>
          <Ionicons name="medical" size={24} color={Colours.primary} />

          <View style={styles.clinicInfo}>
            <Text style={styles.clinicName}>St. Mary&apos;s International</Text>

            <Text style={styles.clinicSub}>{t("profile.savedFacility")}</Text>
          </View>
        </View>

        <View style={styles.clinicCard}>
          <Ionicons name="medical" size={24} color={Colours.primary} />

          <View style={styles.clinicInfo}>
            <Text style={styles.clinicName}>CityMD Urgent Care</Text>

            <Text style={styles.clinicSub}>{t("profile.savedFacility")}</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

type InfoRowProps = {
  label: string;
  value?: string | null;
};

function InfoRow({ label, value }: InfoRowProps) {
  // Missing/empty fields are omitted entirely rather than shown as a
  // label with nothing underneath — same rule used on sos.tsx and
  // show-staff.tsx.
  if (!value) return null;

  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>

      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  content: {
    padding: 20,
    paddingBottom: 40,
  },

  title: {
    ...Typography.h1,
    marginBottom: 24,
  },

  profileHeader: {
    alignItems: "center",
    marginBottom: 24,
  },

  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 12,
  },

  avatarInitials: {
    fontSize: 32,
    fontWeight: "700",
    color: Colours.primary,
  },

  profileName: {
    ...Typography.h3,
    marginBottom: 4,
  },

  profileEmail: {
    color: Colours.muted,
  },

  qrBanner: {
    backgroundColor: Colours.primary,
    borderRadius: 16,
    paddingVertical: 16,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
  },

  qrBannerText: {
    color: "#FFFFFF",
    fontWeight: "700",
    marginLeft: 8,
  },

  syncCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 24,
  },

  syncContent: {
    marginLeft: 12,
    flex: 1,
  },

  syncTitle: {
    fontWeight: "700",
    color: Colours.text,
  },

  syncText: {
    color: Colours.muted,
    marginTop: 2,
  },

  sectionCard: {
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 20,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },

  sectionTitle: {
    ...Typography.body,
    fontWeight: "700",
  },

  editText: {
    color: Colours.primary,
    fontWeight: "700",
  },

  infoRow: {
    marginBottom: 14,
  },

  infoLabel: {
    fontSize: 12,
    color: Colours.muted,
    marginBottom: 2,
  },

  infoValue: {
    color: Colours.text,
  },

  savedTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 12,
  },

  emptyText: {
    color: Colours.muted,
    marginBottom: 12,
  },

  clinicCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 12,
  },

  clinicInfo: {
    marginLeft: 12,
  },

  clinicName: {
    fontWeight: "700",
    color: Colours.text,
  },

  clinicSub: {
    color: Colours.muted,
    marginTop: 2,
  },
});

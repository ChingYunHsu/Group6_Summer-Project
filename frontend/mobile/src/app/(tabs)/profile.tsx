import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
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
import { getFavourites, getVenue, removeFavourite } from "../../services/api";
import { getAccessToken } from "../../services/authService";
import {
  DEFAULT_MEDICAL_PROFILE,
  loadMedicalId,
  MedicalProfile,
} from "../../services/medicalIdService";
import { loadProfile } from "../../services/profileService";
import { Favourite, Venue } from "../../types/venue";

// Derived from the live full_name.
function getInitials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Real user_id values are full UUIDs.
function formatUserId(userId: string): string {
  if (userId.length <= 12) return userId;
  return `${userId.slice(0, 8)}…`;
}

export default function ProfileScreen() {
  const [loading, setLoading] = useState(true);

  // Tracked separately per resource (profile vs. medical), since they're
  // two independent fetches — "synced" only if both succeeded, "offline"
  // if either failed.
  const [profileSyncOk, setProfileSyncOk] = useState<boolean | null>(null);
  const [medicalSyncOk, setMedicalSyncOk] = useState<boolean | null>(null);

  // Combines the two independent sync flags above into one status shown
  // in the sync card.
  const syncStatus: "loading" | "synced" | "offline" =
    profileSyncOk === null || medicalSyncOk === null
      ? "loading"
      : profileSyncOk && medicalSyncOk
        ? "synced"
        : "offline";

  const { t } = useTranslation();

  // Profile and medical ID state, seeded with mock/default data until the
  // real fetches below resolve.
  const [profile, setProfile] = useState(mockProfile);

  const [medicalId, setMedicalId] = useState<MedicalProfile>(
    DEFAULT_MEDICAL_PROFILE,
  );

  // Saved clinics list — each favourite paired with its resolved Venue
  // (or null if that lookup failed).
  const [favourites, setFavourites] = useState<
    { favourite: Favourite; venue: Venue | null }[]
  >([]);

  const [favouritesLoading, setFavouritesLoading] = useState(true);

  const [authStatus, setAuthStatus] = useState<
    "checking" | "guest" | "authenticated"
  >("checking");

  // Runs on every focus: checks auth status, and redirects guests to the
  // guest-profile screen rather than showing this one half-populated.
  useFocusEffect(
    useCallback(() => {
      let isActive = true;

      (async () => {
        const token = await getAccessToken();

        if (!isActive) return;

        if (!token) {
          setAuthStatus("guest");
          router.replace("/profile-guest");
        } else {
          setAuthStatus("authenticated");
        }
      })();

      return () => {
        isActive = false;
      };
    }, []),
  );

  // Loads the real profile once authenticated, and marks whether that
  // fetch succeeded for the sync-status card.
  useFocusEffect(
    useCallback(() => {
      if (authStatus !== "authenticated") return;

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
    }, [authStatus]),
  );

  // Same pattern as above, for the medical ID fetch.
  useFocusEffect(
    useCallback(() => {
      if (authStatus !== "authenticated") return;

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
    }, [authStatus]),
  );

  // Loads saved favourites and resolves each venue_id to a real Venue
  // object for display (name, address).
  useFocusEffect(
    useCallback(() => {
      if (authStatus !== "authenticated") return;

      let isActive = true;

      async function getSavedClinics() {
        try {
          const response = await getFavourites();

          const resolved = await Promise.all(
            response.items.map(async (favourite) => {
              try {
                const venue = await getVenue(favourite.venue_id);
                return { favourite, venue };
              } catch (error) {
                console.error(
                  `Failed to resolve favourite venue ${favourite.venue_id}`,
                  error,
                );
                return { favourite, venue: null };
              }
            }),
          );

          if (isActive) setFavourites(resolved);
        } catch (error) {
          console.error("Failed to load favourites", error);
        } finally {
          if (isActive) setFavouritesLoading(false);
        }
      }

      getSavedClinics();

      return () => {
        isActive = false;
      };
    }, [authStatus]),
  );

  // Optimistic, same pattern as the heart toggle in map.tsx — removes the
  // card immediately rather than waiting on the network, rolling back
  // only if the request actually fails.
  const handleRemoveFavourite = async (venueId: string) => {
    const previous = favourites;

    setFavourites((current) =>
      current.filter((item) => item.favourite.venue_id !== venueId),
    );

    try {
      await removeFavourite(venueId);
    } catch (error) {
      console.error("Failed to remove favourite", error);
      setFavourites(previous);
    }
  };

  if (authStatus !== "authenticated") {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={Colours.primary} />
        </View>
      </SafeAreaView>
    );
  }

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
            <Text style={styles.avatarInitials}>
              {getInitials(profile.full_name)}
            </Text>
          </View>

          <Text style={styles.profileName}>{profile.full_name}</Text>

          <Text style={styles.profileEmail}>{profile.email}</Text>
        </View>

        {/* Sync Status */}

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

            <TouchableOpacity
              testID="profile-edit-personal-info-button"
              onPress={() => router.push("/edit-profile")}
            >
              <Text style={styles.editText}>{t("common.edit")}</Text>
            </TouchableOpacity>
          </View>

          <InfoRow
            label={t("profile.userId")}
            value={profile.user_id ? formatUserId(profile.user_id) : ""}
          />

          <InfoRow label={t("profile.fullName")} value={profile.full_name} />

          <InfoRow label={t("profile.email")} value={profile.email} />

          <InfoRow label={t("profile.phone")} value={profile.phone} />

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

            <TouchableOpacity
              testID="profile-edit-medical-id-button"
              onPress={() => router.push("/medical-id")}
            >
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

        {/* Saved Clinics — sourced from GET /user/favourites, each
            venue_id resolved to a real venue via getVenue(). */}

        <Text style={styles.savedTitle}>{t("profile.savedClinics")}</Text>

        {favouritesLoading ? (
          <ActivityIndicator size="small" color={Colours.primary} />
        ) : favourites.length === 0 ? (
          <Text style={styles.emptyText}>
            {t("profile.noSavedClinics", {
              defaultValue: "No saved clinics yet.",
            })}
          </Text>
        ) : (
          favourites.map(({ favourite, venue }) => (
            <View key={favourite.favourite_id} style={styles.clinicCard}>
              <Ionicons name="medical" size={24} color={Colours.primary} />

              <View style={styles.clinicInfo}>
                <Text style={styles.clinicName}>
                  {venue?.name ?? favourite.venue_id}
                </Text>

                <Text style={styles.clinicSub}>
                  {venue?.address ?? t("profile.savedFacility")}
                </Text>
              </View>

              <TouchableOpacity
                accessibilityLabel="Remove from saved clinics"
                onPress={() => handleRemoveFavourite(favourite.venue_id)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                <Ionicons name="heart" size={22} color="#DC2626" />
              </TouchableOpacity>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

type InfoRowProps = {
  label: string;
  value?: string | null;
};

// Missing/empty fields are omitted entirely rather than shown as a
// label with nothing underneath — same rule used on sos.tsx and
// show-staff.tsx.
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
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  loader: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
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
    flex: 1,
    marginLeft: 12,
    marginRight: 8,
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

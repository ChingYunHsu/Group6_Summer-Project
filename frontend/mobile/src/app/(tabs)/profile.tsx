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

// No real endpoint returns anything like avatar_initials — it was always
// mockProfile.avatar_initials regardless of which real user was logged
// in (this is the same fix already applied in edit-profile.tsx; this
// screen just never got it). Derived from the live full_name instead.
function getInitials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Real user_id values are full UUIDs (e.g.
// "f9c8c0f4-11cc-44e5-a825-376ecae82d7b") — display-only truncation,
// doesn't affect what's actually sent anywhere. Falls back to the raw
// value for anything shorter (e.g. a mock ID) rather than mangling it.
function formatUserId(userId: string): string {
  if (userId.length <= 12) return userId;
  return `${userId.slice(0, 8)}…`;
}

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

  const [favourites, setFavourites] = useState<
    { favourite: Favourite; venue: Venue | null }[]
  >([]);

  const [favouritesLoading, setFavouritesLoading] = useState(true);

  // Drives everything else on this screen now — the previous version had
  // the guest-redirect as a separate, uncoordinated effect that didn't
  // block anything, so profile/medical/favourites all raced ahead and
  // started fetching (and rendering mockProfile/DEFAULT_MEDICAL_PROFILE
  // as their initial state) during the brief window before the redirect
  // actually completed. A guest could see a flash of mock data plus
  // failed 401s before being bounced to profile-guest.tsx. Now nothing
  // else runs, and nothing renders, until this has definitively resolved
  // one way or the other.
  const [authStatus, setAuthStatus] = useState<
    "checking" | "guest" | "authenticated"
  >("checking");

  // useFocusEffect, not plain useEffect — re-checks on every return to
  // this tab, not just first mount, so logging out on another tab and
  // returning here correctly re-triggers the redirect rather than
  // leaving stale authenticated content on screen.
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

  // useFocusEffect, not plain useEffect — this screen previously only
  // fetched once on initial mount ([] dependency array), so saving
  // changes on Edit Profile or Edit Medical ID and navigating back here
  // via router.back() never triggered a refetch; Expo Router keeps this
  // screen mounted the whole time, so the old effect simply never ran
  // again. useFocusEffect re-runs every time this tab is actually
  // navigated to/back to, which is what "refresh on return" needs.
  //
  // Imported from "expo-router" specifically, not "@react-navigation/
  // native" — this project is on Expo SDK 56, where importing
  // useFocusEffect from @react-navigation/native was already confirmed
  // to cause build issues once before (see the same fix applied to
  // settings.tsx earlier in this project).
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

  // Replaces the two hardcoded "St. Mary's International" / "CityMD"
  // entries that never corresponded to any real venue. getFavourites()
  // only returns {venue_id, ...} — each one needs a separate getVenue()
  // call to resolve into something actually displayable (name, address).
  // Runs on focus, same as the two effects above, so favouriting/
  // unfavouriting a venue on the Map tab is reflected here on return.
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

  // "checking" and "guest" both render the same neutral loading state —
  // "guest" specifically because the redirect above is already in
  // flight; showing a spinner for the split second until it completes
  // reads as normal loading, not as a flash of broken/wrong content.
  // mockProfile/DEFAULT_MEDICAL_PROFILE (this screen's initial state)
  // never reach the screen for a guest at all now, since the real
  // content return below is simply never reached.
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

            <TouchableOpacity
              testID="profile-edit-personal-info-button"
              onPress={() => router.push("/edit-profile")}
            >
              <Text style={styles.editText}>{t("common.edit")}</Text>
            </TouchableOpacity>
          </View>

          {/* user_id/email are real now — get_user_profile()'s backend
              response was updated to include both (see profileService.ts).
              No code change needed here; this was already reading
              profile.user_id/profile.email, they're just genuinely
              populated now instead of permanently falling back to
              mockProfile's static placeholders. */}

          <InfoRow
            label={t("profile.userId")}
            value={profile.user_id ? formatUserId(profile.user_id) : ""}
          />

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

        {/* Saved Clinics — now sourced from GET /user/favourites, each
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

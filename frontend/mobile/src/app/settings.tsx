import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Location from "expo-location";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  Alert,
  Linking,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import { featuredLanguages } from "../data/languages";
import { deleteAccount } from "../services/api";
import { logout } from "../services/authService";
import { requestLocationPermission } from "../services/location";
import { clearAccessToken } from "../services/tokenStorage";

export default function SettingsScreen() {
  const { t } = useTranslation();

  const [locationEnabled, setLocationEnabled] = useState(false);

  const [currentLanguageLabel, setCurrentLanguageLabel] = useState<
    string | null
  >(null);

  const [loggingOut, setLoggingOut] = useState(false);

  const [deleting, setDeleting] = useState(false);

  // Re-checks both on every focus, not just first mount — this screen is
  // the return destination for two flows that change these values
  // elsewhere: picking a language on /language, and changing location
  // permission in the system Settings app (which handleLocationToggle
  // itself sends the user to). A mount-only effect would show stale
  // values after either round trip.
  useFocusEffect(
    useCallback(() => {
      let isActive = true;

      (async () => {
        const { status } = await Location.getForegroundPermissionsAsync();
        if (isActive) setLocationEnabled(status === "granted");
      })();

      (async () => {
        const code = await AsyncStorage.getItem("language");
        const match = featuredLanguages.find((lang) => lang.code === code);
        if (isActive) setCurrentLanguageLabel(match ? match.english : null);
      })();

      return () => {
        isActive = false;
      };
    }, []),
  );

  const handleLocationToggle = async (value: boolean) => {
    if (value) {
      const granted = await requestLocationPermission();
      setLocationEnabled(granted);

      if (!granted) {
        Alert.alert(
          t("location.permissionRequired"),
          t("location.permissionRequiredMessage"),
        );
      }

      return;
    }

    // Neither iOS nor Android lets an app revoke its own location
    // permission — only the OS Settings app can. Send the user there
    // rather than silently flipping a switch that doesn't reflect reality.
    Alert.alert(
      t("settings.locationDisableTitle", {
        defaultValue: "Turn off location access",
      }),
      t("settings.locationDisableMessage", {
        defaultValue:
          "Location permissions can only be changed from your device Settings.",
      }),
      [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("location.systemSettings"),
          onPress: () => Linking.openSettings(),
        },
      ],
    );
  };

  const handleLogout = () => {
    Alert.alert(t("settings.logout"), t("settings.logoutMessage"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("settings.logout"),
        style: "destructive",
        onPress: async () => {
          setLoggingOut(true);

          try {
            // Unlike account deletion below, a normal logout does hit the
            // backend (/auth/logout blacklists the token server-side).
            await logout();
          } catch (error) {
            console.error("Logout failed", error);
          } finally {
            setLoggingOut(false);
          }

          router.replace("/");
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      t("settings.deleteAccount"),
      t("settings.deleteAccountMessage"),
      [
        {
          text: t("common.cancel"),
          style: "cancel",
        },
        {
          text: t("common.delete"),
          style: "destructive",
          onPress: async () => {
            setDeleting(true);

            try {
              await deleteAccount();
            } catch (error) {
              console.error("Failed to delete account", error);
              setDeleting(false);

              Alert.alert(
                t("settings.deleteErrorTitle", {
                  defaultValue: "Couldn't delete account",
                }),
                t("settings.deleteErrorMessage", {
                  defaultValue: "Please try again.",
                }),
              );

              return;
            }

            // DELETE /user/account already succeeded server-side at this
            // point. Per spec, everything past here is local-only cleanup
            // — no further backend logout/token-invalidation call.
            await clearAccessToken();

            // Covers "clear locally cached medical profile data," "clear
            // application state," and "clear temporary in-memory caches"
            // in one pass. There's no dedicated medical-data cache key
            // visible in the files I've seen — if one exists elsewhere
            // (e.g. inside medical-id.tsx) and needs different handling,
            // let me know the key and I'll target it specifically instead.
            await AsyncStorage.clear();

            setDeleting(false);

            router.replace("/");
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}

        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <TouchableOpacity
              onPress={() => router.back()}
              style={styles.backButton}
            >
              <Ionicons name="chevron-back" size={24} color={Colours.text} />
            </TouchableOpacity>

            <Text style={styles.title}>{t("settings.title")}</Text>
          </View>

          <View style={styles.avatar}>
            <Ionicons name="person" size={22} color={Colours.primary} />
          </View>
        </View>

        {/* Permissions */}

        <Text style={styles.sectionLabel}>{t("settings.permissions")}</Text>

        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="location" size={20} color={Colours.primary} />

              <Text style={styles.rowText}>{t("settings.enableLocation")}</Text>
            </View>

            <Switch
              value={locationEnabled}
              onValueChange={handleLocationToggle}
              trackColor={{
                false: Colours.borderLight,
                true: Colours.primary,
              }}
            />
          </View>
        </View>

        {/* Account */}

        <Text style={styles.sectionLabel}>{t("settings.account")}</Text>

        <View style={styles.card}>
          <TouchableOpacity
            style={styles.actionRow}
            onPress={() =>
              router.push({ pathname: "/language", params: { origin: "app" } })
            }
          >
            <View style={styles.rowLeft}>
              <Ionicons name="language" size={20} color={Colours.primary} />

              <Text style={styles.rowText}>{t("settings.changeLanguage")}</Text>
            </View>

            <View style={styles.trailing}>
              <Text style={styles.trailingText}>
                {currentLanguageLabel ?? t("settings.currentLanguage")}
              </Text>

              <Ionicons
                name="chevron-forward"
                size={18}
                color={Colours.muted}
              />
            </View>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionRow}
            onPress={handleLogout}
            disabled={loggingOut}
          >
            <View style={styles.rowLeft}>
              <Ionicons
                name="log-out-outline"
                size={20}
                color={Colours.primary}
              />

              <Text style={styles.rowText}>
                {loggingOut
                  ? t("common.loading", { defaultValue: "Loading…" })
                  : t("settings.logout")}
              </Text>
            </View>

            <Ionicons name="chevron-forward" size={18} color={Colours.muted} />
          </TouchableOpacity>
        </View>

        {/* Danger Zone */}

        <Text style={styles.dangerLabel}>{t("settings.dangerZone")}</Text>

        <View style={styles.warningBox}>
          <View style={styles.warningHeader}>
            <Ionicons name="warning" size={18} color={Colours.danger} />

            <Text style={styles.warningText}>
              {t("settings.deleteWarning")}
            </Text>
          </View>
        </View>

        <TouchableOpacity
          testID="settings-delete-account-button"
          style={[styles.deleteButton, deleting && styles.deleteButtonDisabled]}
          onPress={handleDeleteAccount}
          disabled={deleting}
        >
          <Ionicons name="trash" size={18} color={Colours.danger} />

          <Text style={styles.deleteButtonText}>
            {deleting
              ? t("common.loading", { defaultValue: "Loading…" })
              : t("settings.deleteAccount")}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
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

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 32,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
  },

  backButton: {
    marginRight: 12,
  },

  title: {
    ...Typography.h1,
    color: Colours.primary,
  },

  avatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colours.border,
  },

  sectionLabel: {
    ...Typography.caption,
    color: Colours.muted,
    textTransform: "uppercase",
    marginBottom: 10,
    marginLeft: 4,
  },

  dangerLabel: {
    ...Typography.caption,
    color: Colours.danger,
    textTransform: "uppercase",
    marginBottom: 10,
    marginLeft: 4,
    marginTop: 12,
  },

  card: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 28,
    overflow: "hidden",
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
  },

  actionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colours.borderLight,
  },

  rowLeft: {
    flexDirection: "row",
    alignItems: "center",
  },

  rowText: {
    ...Typography.body,
    color: Colours.text,
    marginLeft: 12,
  },

  trailing: {
    flexDirection: "row",
    alignItems: "center",
  },

  trailingText: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginRight: 6,
  },

  warningBox: {
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.danger,
    padding: 16,
    marginBottom: 16,
  },

  warningHeader: {
    flexDirection: "row",
  },

  warningText: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginLeft: 10,
    flex: 1,
  },

  deleteButton: {
    borderWidth: 1,
    borderColor: Colours.danger,
    borderRadius: 999,
    paddingVertical: 18,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  deleteButtonDisabled: {
    opacity: 0.5,
  },

  deleteButtonText: {
    ...Typography.button,
    color: Colours.danger,
    marginLeft: 8,
  },
});

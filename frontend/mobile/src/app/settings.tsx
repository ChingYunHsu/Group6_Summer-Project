import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import {
    Alert,
    SafeAreaView,
    ScrollView,
    StyleSheet,
    Switch,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function SettingsScreen() {
  const [locationEnabled, setLocationEnabled] =
    useState(true);

  const handleLogout = () => {
    Alert.alert(
      "Logout",
      "Logout functionality will be connected to authentication later."
    );
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This action cannot be undone.",
      [
        {
          text: "Cancel",
          style: "cancel",
        },
        {
          text: "Delete",
          style: "destructive",
          onPress: () =>
            console.log(
              "Delete account pressed"
            ),
        },
      ]
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
          <Text style={styles.title}>
            Settings
          </Text>

          <View style={styles.avatar}>
            <Ionicons
              name="person"
              size={22}
              color={Colours.primary}
            />
          </View>
        </View>

        {/* Permissions */}

        <Text style={styles.sectionLabel}>
          Permissions
        </Text>

        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons
                name="location"
                size={20}
                color={Colours.primary}
              />

              <Text style={styles.rowText}>
                Enable Location Access
              </Text>
            </View>

            <Switch
              value={locationEnabled}
              onValueChange={
                setLocationEnabled
              }
              trackColor={{
                false:
                  Colours.borderLight,
                true:
                  Colours.primary,
              }}
            />
          </View>
        </View>

        {/* Account */}

        <Text style={styles.sectionLabel}>
          Account & App
        </Text>

        <View style={styles.card}>
          <TouchableOpacity
            style={styles.actionRow}
            onPress={() =>
              router.push("/")
            }
          >
            <View style={styles.rowLeft}>
              <Ionicons
                name="language"
                size={20}
                color={Colours.primary}
              />

              <Text style={styles.rowText}>
                Change Language
              </Text>
            </View>

            <View style={styles.trailing}>
              <Text
                style={
                  styles.trailingText
                }
              >
                English (US)
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
          >
            <View style={styles.rowLeft}>
              <Ionicons
                name="log-out-outline"
                size={20}
                color={Colours.primary}
              />

              <Text style={styles.rowText}>
                Logout
              </Text>
            </View>

            <Ionicons
              name="chevron-forward"
              size={18}
              color={Colours.muted}
            />
          </TouchableOpacity>
        </View>

        {/* Danger Zone */}

        <Text
          style={styles.dangerLabel}
        >
          Danger Zone
        </Text>

        <View style={styles.warningBox}>
          <View
            style={styles.warningHeader}
          >
            <Ionicons
              name="warning"
              size={18}
              color={Colours.danger}
            />

            <Text
              style={styles.warningText}
            >
              Deleting your account is
              permanent. All medical
              records and profile data
              will be removed.
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={styles.deleteButton}
          onPress={handleDeleteAccount}
        >
          <Ionicons
            name="trash"
            size={18}
            color={Colours.danger}
          />

          <Text
            style={
              styles.deleteButtonText
            }
          >
            Delete my account
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
    justifyContent:
      "space-between",
    alignItems: "center",
    marginBottom: 32,
  },

  title: {
    ...Typography.h1,
    color: Colours.primary,
  },

  avatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor:
      Colours.surfaceLight,
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
    backgroundColor:
      Colours.surfaceLight,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    marginBottom: 28,
    overflow: "hidden",
  },

  row: {
    flexDirection: "row",
    justifyContent:
      "space-between",
    alignItems: "center",
    padding: 16,
  },

  actionRow: {
    flexDirection: "row",
    justifyContent:
      "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor:
      Colours.borderLight,
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
    backgroundColor:
      Colours.surfaceLight,
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

  deleteButtonText: {
    ...Typography.button,
    color: Colours.danger,
    marginLeft: 8,
  },
});
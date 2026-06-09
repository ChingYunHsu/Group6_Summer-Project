import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import {
    Alert,
    SafeAreaView,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import {
    getCurrentLocation,
    requestLocationPermission,
} from "../services/location";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

export default function LocationScreen() {
    const [locationEnabled, setLocationEnabled] =
        useState(false);

    const [isLoading, setIsLoading] =
        useState(false);

  const handleLocationAccess = async () => {
  try {
    setIsLoading(true);

    const granted =
      await requestLocationPermission();

    if (!granted) {
      Alert.alert(
        "Location Permission Required",
        "ClearPath uses your location to show nearby clinics, pharmacies, and routing information."
      );

      return;
    }

    const location =
      await getCurrentLocation();

    if (!location) {
      Alert.alert(
        "Unable to Retrieve Location",
        "Please ensure GPS is enabled on your device."
      );

      return;
    }

    console.log(
      "User coordinates:",
      location
    );

    setLocationEnabled(true);

    Alert.alert(
      "Location Enabled",
      "Location services have been successfully enabled."
    );
  } catch (error) {
    console.error(error);

    Alert.alert(
      "Location Error",
      "Something went wrong while accessing location services."
    );
  } finally {
    setIsLoading(false);
  }
};

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Progress Bar */}

        <View style={styles.progressTrack}>
          <View style={styles.progressFill} />
        </View>

        {/* Illustration */}

        <View style={styles.illustrationWrapper}>
          <View style={styles.illustrationCircle}>
            <Ionicons
              name="location"
              size={90}
              color={Colours.primary}
            />
          </View>
        </View>

        {/* Header */}

        <Text style={styles.title}>
          Help us find you
        </Text>

        <Text style={styles.subtitle}>
          We&apos;ll use your location to show
          the nearest clinics and hospitals
          with the shortest wait times.
        </Text>

        {/* Location Card */}

        <TouchableOpacity
          style={[
            styles.locationCard,
            locationEnabled &&
              styles.locationCardActive,
          ]}
          onPress={handleLocationAccess}
        >
          <View style={styles.iconCircle}>
  <Ionicons
    name={
      locationEnabled
        ? "checkmark-circle"
        : "location"
    }
    size={24}
    color={
      locationEnabled
        ? Colours.success
        : Colours.primary
    }
  />
</View>

          <View style={styles.locationText}>
            <Text style={styles.locationTitle}>
  {locationEnabled
    ? "Location Enabled"
    : "Enable Location Access"}
</Text>

            <Text style={styles.locationSubtitle}>
            {locationEnabled
                ? "GPS permission granted"
                : "Recommended for accurate travel times"}
            </Text>
          </View>

          <Text style={styles.chevron}>
            ›
          </Text>
        </TouchableOpacity>

        {/* Privacy Box */}

        <View style={styles.privacyBox}>
          <Text style={styles.lockIcon}>
            🔒
          </Text>

          <Text style={styles.privacyText}>
            Your location data is private.
            We never share your history or
            medical records with third
            parties without your consent.
          </Text>
        </View>

        {/* GPS Tip */}

        <Text style={styles.tipText}>
          Device GPS is highly recommended
          for route searching.
        </Text>

        {/* Continue */}

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() =>
            router.push("/auth-gateway")
          }
        >
          <Text
            style={styles.primaryButtonText}
          >
            Continue →
          </Text>
        </TouchableOpacity>

        {/* Skip */}

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() =>
            router.push("/auth-gateway")
          }
        >
          <Text
            style={
              styles.secondaryButtonText
            }
          >
            I&apos;ll do this later
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
    alignItems: "center",
  },

  progressTrack: {
    width: "100%",
    height: 6,
    backgroundColor: Colours.borderLight,
    borderRadius: 999,
    overflow: "hidden",
    marginTop: 10,
  },

  progressFill: {
    width: "50%",
    height: "100%",
    backgroundColor: Colours.primary,
  },

  illustrationWrapper: {
    marginTop: 40,
    marginBottom: 32,
  },

  illustrationCircle: {
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colours.border,
  },

  title: {
    ...Typography.h1,
    color: Colours.text,
    textAlign: "center",
    marginBottom: 12,
  },

  subtitle: {
    ...Typography.body,
    color: Colours.muted,
    textAlign: "center",
    lineHeight: 28,
    marginBottom: 36,
    maxWidth: 320,
  },

  locationCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.borderLight,
    padding: 16,
    width: "100%",
    marginBottom: 16,
  },

  locationCardActive: {
    backgroundColor: Colours.surfaceLight,
    borderColor: Colours.primary,
  },

  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },

  checkIcon: {
    fontSize: 22,
    color: Colours.success,
    fontWeight: "700",
  },

  locationText: {
    flex: 1,
  },

  locationTitle: {
    ...Typography.body,
    color: Colours.text,
    fontWeight: "700",
  },

  locationSubtitle: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginTop: 4,
  },

  chevron: {
    fontSize: 24,
    color: Colours.disabled,
  },

  privacyBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    padding: 16,
    width: "100%",
    marginBottom: 28,
  },

  lockIcon: {
    fontSize: 18,
    marginRight: 10,
  },

  privacyText: {
    ...Typography.bodySmall,
    color: Colours.muted,
    flex: 1,
    lineHeight: 22,
  },

  tipText: {
    ...Typography.caption,
    color: Colours.muted,
    textAlign: "center",
    marginBottom: 28,
  },

  primaryButton: {
    width: "100%",
    backgroundColor: Colours.primary,
    borderRadius: 999,
    paddingVertical: 18,
    marginBottom: 14,
  },

  primaryButtonText: {
    ...Typography.button,
    color: Colours.surface,
    textAlign: "center",
  },

  secondaryButton: {
    width: "100%",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 999,
    paddingVertical: 18,
  },

  secondaryButtonText: {
    ...Typography.button,
    color: Colours.muted,
    textAlign: "center",
  },
});
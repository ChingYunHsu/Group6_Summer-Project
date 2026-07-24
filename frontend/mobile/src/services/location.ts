import * as Location from "expo-location";

export type UserLocation = {
  latitude: number;
  longitude: number;
};

// Requests foreground location permission, returns whether it was
// granted.
export async function requestLocationPermission(): Promise<boolean> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();

    return status === "granted";
  } catch (error) {
    console.error("Location permission error:", error);

    return false;
  }
}

// Gets the device's current position. Uses Balanced accuracy rather
// than High/Highest — on Android emulators specifically, requesting
// high-accuracy GPS can fail entirely (ERR_CURRENT_LOCATION_IS_UNAVAILABLE)
// since emulators don't simulate a real satellite fix, while a mock
// coordinate set via the emulator's location controls is still honoured
// at Balanced accuracy.
export async function getCurrentLocation(): Promise<UserLocation | null> {
  try {
    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });

    return {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
    };
  } catch (error) {
    console.error("Location retrieval error:", error);

    return null;
  }
}

/**
 * Haversine distance calculation
 * Returns distance in KM
 */
export function calculateDistance(
  userLat: number,
  userLng: number,
  venueLat: number,
  venueLng: number,
): number {
  const R = 6371;

  const dLat = ((venueLat - userLat) * Math.PI) / 180;

  const dLng = ((venueLng - userLng) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((userLat * Math.PI) / 180) *
      Math.cos((venueLat * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return Number((R * c).toFixed(1));
}

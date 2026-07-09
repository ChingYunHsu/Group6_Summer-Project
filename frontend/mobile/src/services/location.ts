import * as Location from "expo-location";

export type UserLocation = {
  latitude: number;
  longitude: number;
};

export async function requestLocationPermission(): Promise<boolean> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();

    return status === "granted";
  } catch (error) {
    console.error("Location permission error:", error);

    return false;
  }
}

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

import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MapView, { Polyline } from "react-native-maps";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import CategoryChips, { Category } from "../../components/CategoryChips";
import FilterModal from "../../components/FilterModal";
import FloatingActionButtons from "../../components/FloatingActionButtons";
import LocationRequiredModal from "../../components/LocationRequiredModal";
import LoginRequiredModal from "../../components/LoginRequiredModal";
import MapSearchBar from "../../components/MapSearchBar";
import ReportBottomSheet from "../../components/ReportBottomSheet";
import ReportMarker from "../../components/ReportMarker";
import ReportModal from "../../components/ReportModal";
import RouteDetailModal from "../../components/RouteDetailModal";
import RouteOptionsModal from "../../components/RouteOptionsModal";
import VenueBottomSheet from "../../components/VenueBottomSheet";
import VenueMarker from "../../components/VenueMarker";
import { Colours } from "../../constants/colours";
import { getAccessToken } from "../../services/authService";
import {
  addFavourite,
  confirmReport,
  getFavourites,
  getReports,
  getRouteDetail,
  getRouteOptions,
  getVenueBusyness,
  getVenues,
  removeFavourite,
  submitReport,
} from "../../services/api";
import {
  getCurrentLocation,
  requestLocationPermission,
  calculateDistance,
} from "../../services/location";
import { Report, RouteDetail, RouteOption, Venue } from "../../types/venue";

const INITIAL_REGION = {
  latitude: 40.758,
  longitude: -73.9855,
  latitudeDelta: 0.08,
  longitudeDelta: 0.08,
};
const DEFAULT_LOCATION = {
  latitude: INITIAL_REGION.latitude,
  longitude: INITIAL_REGION.longitude,
};

// Clinic groups four raw venue_type values together per the medical
// venue coverage SOP — healthcare/dentist/laboratory venues have no
// filter chip of their own, so they'd otherwise be unreachable through
// the category filter UI at all. Hospital and Pharmacy stay separate,
// unaffected by this grouping.
function matchesCategory(venue: Venue, category: Category): boolean {
  switch (category) {
    case "Clinic":
      return (
        venue.venue_type === "clinic" ||
        venue.venue_type === "healthcare" ||
        venue.venue_type === "dentist" ||
        venue.venue_type === "laboratory"
      );
    case "Pharmacy":
      return venue.venue_type === "pharmacy";
    case "AED":
      return venue.venue_type === "emergencyasset";
    case "Hospital":
      return venue.venue_type === "hospital";
    case "Restroom":
      return venue.venue_type === "restroom";
    default:
      return false;
  }
}

const LEGEND_ITEMS = [
  {
    translationKey: "map.filters.quiet",
    defaultValue: "Quiet",
    colour: "#16A34A",
  },
  {
    translationKey: "map.filters.moderate",
    defaultValue: "Moderate",
    colour: "#FACC15",
  },
  {
    translationKey: "map.filters.busy",
    defaultValue: "Busy",
    colour: "#DC2626",
  },
  {
    translationKey: "map.filters.unknown",
    defaultValue: "Unknown",
    colour: "#2563EB",
  },
] as const;

export default function MapScreen() {
  const { t } = useTranslation();

  const [venues, setVenues] = useState<Venue[]>([]);

  const [reports, setReports] = useState<Report[]>([]);

  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [category, setCategory] = useState<Category>("Clinic");

  const [selectedVenueId, setSelectedVenueId] = useState<string | null>(null);

  const selectedVenue = useMemo(
    () => venues.find((v) => v.venue_id === selectedVenueId) ?? null,
    [venues, selectedVenueId],
  );

  const activeReportForSelectedVenue = useMemo(() => {
    if (!selectedVenueId) return null;

    return (
      reports.find(
        (r) => r.venue_id === selectedVenueId && r.status === "active",
      ) ?? null
    );
  }, [reports, selectedVenueId]);

  const [venueVisible, setVenueVisible] = useState(false);

  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const selectedReport = useMemo(
    () => reports.find((r) => r.report_id === selectedReportId) ?? null,
    [reports, selectedReportId],
  );

  const [reportSheetVisible, setReportSheetVisible] = useState(false);

  const [filterVisible, setFilterVisible] = useState(false);

  const [reportVisible, setReportVisible] = useState(false);

  const [loginModalVisible, setLoginModalVisible] = useState(false);

  const [openNow, setOpenNow] = useState<boolean | undefined>(undefined);

  const [wheelchairAccess, setWheelchairAccess] = useState<
    "full_access" | "partial_or_full" | undefined
  >(undefined);

  const [language, setLanguage] = useState("");

  const [autoCurrentTime, setAutoCurrentTime] = useState(true);

  const [liveStatus, setLiveStatus] = useState<
    "quiet" | "moderate" | "busy" | undefined
  >(undefined);

  const [timeOffset, setTimeOffset] = useState(0);

  const [routeOptionsVisible, setRouteOptionsVisible] = useState(false);

  const [routeDetailVisible, setRouteDetailVisible] = useState(false);

  const [locationModalVisible, setLocationModalVisible] = useState(false);

  const [selectedMode, setSelectedMode] = useState("walk");

  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);

  const [routeDetail, setRouteDetail] = useState<RouteDetail | null>(null);

  const [selectedRouteDuration, setSelectedRouteDuration] = useState(0);

  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [favouriteVenueIds, setFavouriteVenueIds] = useState<Set<string>>(
    new Set(),
  );

  const [busynessFetchedIds, setBusynessFetchedIds] = useState<Set<string>>(
    new Set(),
  );

  const [locationEnabled, setLocationEnabled] = useState(false);

  const [currentLocation, setCurrentLocation] = useState(DEFAULT_LOCATION);

  const mapRef = useRef<MapView>(null);

  const [region, setRegion] = useState(INITIAL_REGION);

  useEffect(() => {
    (async () => {
      const token = await getAccessToken();
      setIsAuthenticated(!!token);
    })();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: clears stale favourites immediately when auth is lost, same justified pattern as loadData's effect below
      setFavouriteVenueIds(new Set());
      return;
    }

    (async () => {
      try {
        const response = await getFavourites();
        setFavouriteVenueIds(new Set(response.items.map((f) => f.venue_id)));
      } catch (error) {
        console.error("Failed to load favourites", error);
      }
    })();
  }, [isAuthenticated]);

  useEffect(() => {
    (async () => {
      const servicesEnabled = await Location.hasServicesEnabledAsync();

      if (!servicesEnabled) {
        setLocationEnabled(false);
        return;
      }

      const granted = await requestLocationPermission();

      if (!granted) {
        setLocationEnabled(false);
        return;
      }

      const position = await getCurrentLocation();

      if (!position) {
        setLocationEnabled(false);
        return;
      }

      setCurrentLocation(position);
      setLocationEnabled(true);
    })();
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);

    try {
      const [venueData, reportData] = await Promise.all([
        getVenues({
          open_now: openNow,
          languages: language ? [language] : [],
        }),
        getReports(),
      ]);

      setVenues(venueData);
      setReports(reportData);
      setBusynessFetchedIds(new Set());
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [openNow, language]);

  async function refreshReports() {
    try {
      const reportData = await getReports();
      setReports(reportData);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleDirections() {
    const enabled = await Location.hasServicesEnabledAsync();

    if (!enabled) {
      setLocationModalVisible(true);

      return;
    }

    const freshPosition = await getCurrentLocation();

    if (!freshPosition) {
      setLocationModalVisible(true);

      return;
    }

    setCurrentLocation(freshPosition);
    setLocationEnabled(true);

    setVenueVisible(false);

    try {
      const response = await getRouteOptions(
        selectedVenue?.venue_id,
        freshPosition,
      );
      setRouteOptions(response.options);
    } catch (error) {
      console.error(error);
      setRouteOptions([]);
    }

    setSelectedMode("walk");

    setRouteOptionsVisible(true);
  }

  async function handleRouteSelected(route: RouteOption) {
    setRouteOptionsVisible(false);

    setSelectedRouteDuration(route.duration_minutes);
    setSelectedMode(route.mode);

    try {
      const detail = await getRouteDetail(
        selectedVenue?.venue_id,
        currentLocation,
        route.mode,
      );
      setRouteDetail(detail);
    } catch (error) {
      console.error(error);
      setRouteDetail(null);
    }

    setRouteDetailVisible(true);
  }

  async function handleStartNavigation() {
    if (!selectedVenue) {
      setRouteDetailVisible(false);
      return;
    }

    const destLat = Number(selectedVenue.latitude);
    const destLng = Number(selectedVenue.longitude);
    const originLat = currentLocation.latitude;
    const originLng = currentLocation.longitude;

    const appleDirflg =
      selectedMode === "walk" ? "w" : selectedMode === "drive" ? "d" : "r";

    const googleTravelMode =
      selectedMode === "walk"
        ? "walking"
        : selectedMode === "drive"
          ? "driving"
          : "transit";

    const appleMapsUrl = `http://maps.apple.com/?saddr=${originLat},${originLng}&daddr=${destLat},${destLng}&dirflg=${appleDirflg}`;
    const googleMapsWebUrl = `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLng}&destination=${destLat},${destLng}&travelmode=${googleTravelMode}`;

    const primaryUrl = Platform.OS === "ios" ? appleMapsUrl : googleMapsWebUrl;

    try {
      const supported = await Linking.canOpenURL(primaryUrl);
      await Linking.openURL(supported ? primaryUrl : googleMapsWebUrl);
    } catch (error) {
      console.error("Failed to open navigation app", error);
      try {
        await Linking.openURL(googleMapsWebUrl);
      } catch (fallbackError) {
        console.error("Failed to open fallback maps URL", fallbackError);
      }
    }

    setRouteDetailVisible(false);
  }

  const handleReportConfirmation = useCallback(
    async (reportId: string, action: "still_here" | "resolved") => {
      if (!isAuthenticated) {
        setLoginModalVisible(true);
        return;
      }

      try {
        await confirmReport(reportId, action);
      } catch (error) {
        console.error(error);
      }

      await refreshReports();
    },
    [isAuthenticated],
  );

  const handleToggleFavourite = useCallback(async () => {
    if (!isAuthenticated) {
      setLoginModalVisible(true);
      return;
    }

    if (!selectedVenue) return;

    const venueId = selectedVenue.venue_id;
    const wasFavourite = favouriteVenueIds.has(venueId);

    setFavouriteVenueIds((current) => {
      const next = new Set(current);
      if (wasFavourite) {
        next.delete(venueId);
      } else {
        next.add(venueId);
      }
      return next;
    });

    try {
      if (wasFavourite) {
        await removeFavourite(venueId);
      } else {
        await addFavourite(venueId);
      }
    } catch (error) {
      console.error("Failed to toggle favourite", error);

      setFavouriteVenueIds((current) => {
        const next = new Set(current);
        if (wasFavourite) {
          next.add(venueId);
        } else {
          next.delete(venueId);
        }
        return next;
      });
    }
  }, [isAuthenticated, selectedVenue, favouriteVenueIds]);

  const handleSelectSearchSuggestion = useCallback((venue: Venue) => {
    setSearch("");
    setSelectedVenueId(venue.venue_id);
    setVenueVisible(true);

    mapRef.current?.animateToRegion(
      {
        latitude: Number(venue.latitude),
        longitude: Number(venue.longitude),
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      },
      400,
    );
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect, intentional fetch-on-dependency-change
    loadData();
  }, [loadData]);

  const filteredVenues = useMemo(() => {
    return venues.filter((venue) => {
      const matchesSearch = venue.name
        .toLowerCase()
        .includes(search.toLowerCase());

      const matchesLiveStatus =
        !liveStatus || venue.busyness?.busyness_status === liveStatus;

      const matchesWheelchairAccess =
        !wheelchairAccess ||
        (wheelchairAccess === "full_access"
          ? venue.accessible_status === "full_access"
          : venue.accessible_status === "full_access" ||
            venue.accessible_status === "partial");

      return (
        matchesSearch &&
        matchesCategory(venue, category) &&
        matchesLiveStatus &&
        matchesWheelchairAccess
      );
    });
  }, [venues, search, category, liveStatus, wheelchairAccess]);

  const searchSuggestions = useMemo(() => {
    if (!search.trim()) return [];

    return venues
      .filter(
        (venue) =>
          matchesCategory(venue, category) &&
          venue.name.toLowerCase().includes(search.toLowerCase()),
      )
      .slice(0, 6);
  }, [venues, search, category]);

  const nearestVenuesForReport = useMemo(() => {
    const withDistance = venues.map((venue) => ({
      venue,
      distance: calculateDistance(
        currentLocation.latitude,
        currentLocation.longitude,
        Number(venue.latitude),
        Number(venue.longitude),
      ),
    }));

    withDistance.sort((a, b) => a.distance - b.distance);

    return withDistance.slice(0, 5).map((item) => item.venue);
  }, [venues, currentLocation]);

  useEffect(() => {
    const venuesNeedingBusyness = venues.filter(
      (v) =>
        matchesCategory(v, category) && !busynessFetchedIds.has(v.venue_id),
    );

    if (venuesNeedingBusyness.length === 0) return;

    let isActive = true;

    Promise.all(
      venuesNeedingBusyness.map((venue) =>
        getVenueBusyness(venue.venue_id)
          .then((result) => ({
            venueId: venue.venue_id,
            busyness: result?.busyness,
          }))
          .catch(() => ({ venueId: venue.venue_id, busyness: undefined })),
      ),
    ).then((results) => {
      if (!isActive) return;

      setVenues((current) =>
        current.map((v) => {
          const match = results.find((r) => r.venueId === v.venue_id);
          return match?.busyness ? { ...v, busyness: match.busyness } : v;
        }),
      );

      setBusynessFetchedIds((current) => {
        const next = new Set(current);
        results.forEach((r) => next.add(r.venueId));
        return next;
      });
    });

    return () => {
      isActive = false;
    };
  }, [venues, category, busynessFetchedIds]);

  const handleZoomIn = () => {
    const nextRegion = {
      ...region,
      latitudeDelta: region.latitudeDelta / 2,
      longitudeDelta: region.longitudeDelta / 2,
    };

    mapRef.current?.animateToRegion(nextRegion, 300);
  };

  const handleZoomOut = () => {
    const nextRegion = {
      ...region,
      latitudeDelta: region.latitudeDelta * 2,
      longitudeDelta: region.longitudeDelta * 2,
    };
    mapRef.current?.animateToRegion(nextRegion, 300);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.loader}>
        <ActivityIndicator size="large" color={Colours.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFill}
        initialRegion={INITIAL_REGION}
        onRegionChangeComplete={setRegion}
        showsUserLocation
      >
        {filteredVenues.map((venue) => (
          <VenueMarker
            key={venue.venue_id}
            venue={venue}
            showLiveStatus={autoCurrentTime}
            onPress={() => {
              setSelectedVenueId(venue.venue_id);
              setVenueVisible(true);
            }}
          />
        ))}

        {reports.map((report) => (
          <ReportMarker
            key={report.report_id}
            report={report}
            onPress={(pressedReport) => {
              setSelectedReportId(pressedReport.report_id);
              setReportSheetVisible(true);
            }}
          />
        ))}

        {routeDetail?.polyline_preview &&
          routeDetail.polyline_preview.length > 0 && (
            <Polyline
              coordinates={routeDetail.polyline_preview}
              strokeColor={Colours.primary}
              strokeWidth={4}
            />
          )}
      </MapView>

      <View style={styles.topOverlay}>
        <MapSearchBar
          value={search}
          onChangeText={setSearch}
          onFilterPress={() => setFilterVisible(true)}
          suggestions={searchSuggestions}
          onSelectSuggestion={handleSelectSearchSuggestion}
        />

        <CategoryChips selected={category} onSelect={setCategory} />
      </View>

      <View style={styles.zoomControls}>
        <TouchableOpacity style={styles.zoomButton} onPress={handleZoomIn}>
          <Ionicons name="add" size={24} color={Colours.text} />
        </TouchableOpacity>

        <View style={styles.zoomDivider} />

        <TouchableOpacity style={styles.zoomButton} onPress={handleZoomOut}>
          <Ionicons name="remove" size={24} color={Colours.text} />
        </TouchableOpacity>
      </View>

      {autoCurrentTime && (
        <View style={styles.legendContainer}>
          {LEGEND_ITEMS.map((item, index) => (
            <View
              key={item.translationKey}
              style={[
                styles.legendRow,
                index === LEGEND_ITEMS.length - 1 && styles.legendLastRow,
              ]}
            >
              <View
                style={[styles.legendDot, { backgroundColor: item.colour }]}
              />
              <Text style={styles.legendLabel}>
                {t(item.translationKey, { defaultValue: item.defaultValue })}
              </Text>
            </View>
          ))}
        </View>
      )}

      <FloatingActionButtons
        onSOSPress={() => router.push("/sos")}
        onReportPress={() => setReportVisible(true)}
      />

      {routeDetail?.polyline_preview &&
        routeDetail.polyline_preview.length > 0 && (
          <TouchableOpacity
            style={styles.clearRouteButton}
            onPress={() => setRouteDetail(null)}
          >
            <Ionicons name="close-circle" size={18} color={Colours.text} />

            <Text style={styles.clearRouteText}>Clear Route</Text>
          </TouchableOpacity>
        )}

      <FilterModal
        visible={filterVisible}
        openNow={openNow}
        wheelchairAccess={wheelchairAccess}
        language={language}
        autoCurrentTime={autoCurrentTime}
        onClose={() => setFilterVisible(false)}
        onApply={(filters) => {
          setOpenNow(filters.openNow);

          setWheelchairAccess(filters.wheelchairAccess);

          setLanguage(filters.language);

          setAutoCurrentTime(filters.autoCurrentTime);

          setLiveStatus(filters.liveStatus);

          setTimeOffset(filters.timeOffset);
        }}
      />

      <ReportModal
        visible={reportVisible}
        onClose={() => setReportVisible(false)}
        isAuthenticated={isAuthenticated}
        locationEnabled={locationEnabled}
        currentLocation={currentLocation}
        nearbyVenues={nearestVenuesForReport}
        onRequireLogin={() => setLoginModalVisible(true)}
        onRequireLocation={() => setLocationModalVisible(true)}
        onSubmitVenue={async (report) => {
          try {
            await submitReport({
              venue_id: report.venueId,
              issue_type: report.issueType,
              latitude: report.latitude,
              longitude: report.longitude,
              description: report.description || undefined,
            });

            setVenues((current) =>
              current.map((venue) => {
                if (venue.venue_id !== report.venueId) {
                  return venue;
                }

                return {
                  ...venue,

                  active_warning: true,

                  live_report_count: (venue.live_report_count ?? 0) + 1,
                };
              }),
            );
          } catch (error) {
            console.error(error);
          }

          await refreshReports();

          setReportVisible(false);
        }}
        onSubmitIncident={async (report) => {
          try {
            await submitReport({
              issue_type: report.issueType,
              latitude: report.latitude,
              longitude: report.longitude,
              description: report.description || undefined,
            });
          } catch (error) {
            console.error(error);
          }

          await refreshReports();

          setReportVisible(false);
        }}
      />

      <VenueBottomSheet
        visible={venueVisible}
        venue={selectedVenue}
        activeReport={activeReportForSelectedVenue}
        autoCurrentTime={autoCurrentTime}
        timeOffset={timeOffset}
        isFavourite={
          selectedVenue ? favouriteVenueIds.has(selectedVenue.venue_id) : false
        }
        onToggleFavourite={handleToggleFavourite}
        onClose={() => setVenueVisible(false)}
        onDirectionsPress={handleDirections}
        onConfirmReport={(reportId) =>
          handleReportConfirmation(reportId, "still_here")
        }
        onResolveReport={(reportId) =>
          handleReportConfirmation(reportId, "resolved")
        }
      />

      <ReportBottomSheet
        visible={reportSheetVisible}
        report={selectedReport}
        onClose={() => setReportSheetVisible(false)}
        onConfirm={(reportId) =>
          handleReportConfirmation(reportId, "still_here")
        }
        onResolve={(reportId) => handleReportConfirmation(reportId, "resolved")}
      />

      <RouteOptionsModal
        visible={routeOptionsVisible}
        routes={routeOptions}
        originLabel="Current Location"
        departureTime="Now"
        selectedMode={selectedMode}
        onSelectMode={setSelectedMode}
        onSelectRoute={handleRouteSelected}
        onClose={() => setRouteOptionsVisible(false)}
      />

      <RouteDetailModal
        visible={routeDetailVisible}
        destinationName={selectedVenue?.name ?? ""}
        durationMinutes={selectedRouteDuration}
        steps={routeDetail?.steps ?? []}
        onStartNavigation={handleStartNavigation}
        onClose={() => setRouteDetailVisible(false)}
      />

      <LocationRequiredModal
        visible={locationModalVisible}
        onClose={() => setLocationModalVisible(false)}
      />

      <LoginRequiredModal
        visible={loginModalVisible}
        onClose={() => setLoginModalVisible(false)}
      />
    </SafeAreaView>
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

    backgroundColor: Colours.background,
  },

  topOverlay: {
    position: "absolute",

    top: 60,

    left: 20,

    right: 20,
  },

  clearRouteButton: {
    position: "absolute",

    left: 20,

    bottom: 36,

    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 999,

    paddingVertical: 10,

    paddingHorizontal: 16,

    shadowColor: "#000",

    shadowOpacity: 0.15,

    shadowRadius: 6,

    shadowOffset: {
      width: 0,

      height: 2,
    },

    elevation: 5,
  },

  clearRouteText: {
    marginLeft: 6,

    fontWeight: "600",

    color: Colours.text,
  },

  zoomControls: {
    position: "absolute",
    right: 20,
    top: 220,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 5,
  },

  zoomButton: {
    width: 44,
    height: 44,
    justifyContent: "center",
    alignItems: "center",
  },

  zoomDivider: {
    height: 1,
    backgroundColor: Colours.border,
    marginHorizontal: 8,
  },

  legendContainer: {
    position: "absolute",
    left: 20,
    bottom: 96,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 5,
  },

  legendRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },

  legendLastRow: {
    marginBottom: 0,
  },

  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },

  legendLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: Colours.text,
  },
});

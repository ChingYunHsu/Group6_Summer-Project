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

// Shared by filteredVenues and the busyness-fetching effect below — both
// need the same "which venues match the selected category" logic, and
// duplicating this switch in two places risked them silently drifting
// apart over time.
function matchesCategory(venue: Venue, category: Category): boolean {
  switch (category) {
    case "Clinic":
      return venue.venue_type === "clinic";
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

export default function MapScreen() {
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

  // The active report (if any) driving the selected venue's active_warning
  // flag, so VenueBottomSheet can show real "reported X ago / N
  // confirmations" data instead of a hardcoded placeholder.
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

  // Undefined = "no preference sent to the API" — NOT the same as `false`.
  // getVenues() only sets the `accessible`/`open_now` query params when the
  // filter value isn't undefined, so leaving these undefined until the user
  // actually applies a filter means the first load isn't silently
  // restricted to "only non-accessible, currently-closed venues."
  const [openNow, setOpenNow] = useState<boolean | undefined>(undefined);

  const [accessible, setAccessible] = useState<boolean | undefined>(undefined);

  const [language, setLanguage] = useState("");

  const [autoCurrentTime, setAutoCurrentTime] = useState(true);

  // Now actually read below in filteredVenues, filtering by
  // venue.busyness?.busyness_status — previously the value was
  // discarded entirely ([, setLiveStatus]), so selecting a Live Status
  // chip updated state that nothing ever checked.
  const [liveStatus, setLiveStatus] = useState<
    "quiet" | "moderate" | "busy" | undefined
  >(undefined);

  // Unlike liveStatus, this one IS actually read — forwarded straight
  // through to VenueBottomSheet, which looks up the matching entry in
  // its own already-fetched 12-hour forecast data. 0 = Now.
  const [timeOffset, setTimeOffset] = useState(0);

  const [routeOptionsVisible, setRouteOptionsVisible] = useState(false);

  const [routeDetailVisible, setRouteDetailVisible] = useState(false);

  const [locationModalVisible, setLocationModalVisible] = useState(false);

  const [selectedMode, setSelectedMode] = useState("walk");

  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);

  const [routeDetail, setRouteDetail] = useState<RouteDetail | null>(null);

  // The real /routes/detail response has no duration field (see
  // types/venue.ts) — the duration shown in RouteDetailModal comes from
  // whichever RouteOption the user picked in RouteOptionsModal instead.
  const [selectedRouteDuration, setSelectedRouteDuration] = useState(0);

  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Set of venue_id, not full Favourite objects — all this screen needs
  // is fast "is this venue favourited" lookups for the heart icon in
  // VenueBottomSheet; the richer fields (favourite_id, saved_at,
  // display_status) only matter where favourites are actually listed
  // (profile.tsx), not here.
  const [favouriteVenueIds, setFavouriteVenueIds] = useState<Set<string>>(
    new Set(),
  );

  // Tracks which venue_ids busyness has already been fetched FOR,
  // regardless of whether that fetch actually succeeded — deliberately
  // separate from checking venue.busyness itself, since a failed fetch
  // also leaves that undefined. Without this separate guard, a venue
  // whose busyness request genuinely fails (e.g. the known current-
  // status date-window bug) would be retried forever, since it would
  // keep looking like "never fetched" on every re-render.
  const [busynessFetchedIds, setBusynessFetchedIds] = useState<Set<string>>(
    new Set(),
  );

  const [locationEnabled, setLocationEnabled] = useState(false);

  const [currentLocation, setCurrentLocation] = useState(DEFAULT_LOCATION);

  // ---------------------------------------------------------------------
  // Auth + device location — previously hardcoded TEMP VALUES.
  // ---------------------------------------------------------------------

  useEffect(() => {
    (async () => {
      const token = await getAccessToken();
      setIsAuthenticated(!!token);
    })();
  }, []);

  // Favourites require a real login (require_bearer_auth server-side) —
  // guests never have any to fetch, and clearing the set when auth is
  // lost (e.g. logout mid-session) avoids showing stale hearts for a
  // previous user.
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

  // Fetches venues + reports whenever the active filters change. Wrapped
  // in useCallback so it can safely be listed as an effect dependency
  // below (resolves the exhaustive-deps warning) without recreating a new
  // function identity on every render.
  const loadData = useCallback(async () => {
    setLoading(true);

    try {
      const [venueData, reportData] = await Promise.all([
        getVenues({
          open_now: openNow,
          accessible,
          languages: language ? [language] : [],
        }),
        getReports(),
      ]);

      setVenues(venueData);
      setReports(reportData);
      // A fresh venue list means fresh objects with no busyness attached
      // yet, even for venue_ids seen before — reset the guard so the
      // effect below knows to fetch for all of them again.
      setBusynessFetchedIds(new Set());
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [openNow, accessible, language]);

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

  // "Start Navigation" hands off to the device's own maps app rather than
  // building in-app turn-by-turn (live GPS tracking, rerouting, voice
  // guidance) — a much bigger feature than this button implies. Apple
  // Maps on iOS since it's always installed with no extra dependency;
  // Google's cross-platform web URL as a universal fallback (opens the
  // Google Maps app if installed, otherwise a browser) if the primary
  // deep link can't be opened for any reason.
  async function handleStartNavigation() {
    if (!selectedVenue) {
      setRouteDetailVisible(false);
      return;
    }

    const destLat = Number(selectedVenue.latitude);
    const destLng = Number(selectedVenue.longitude);
    const originLat = currentLocation.latitude;
    const originLng = currentLocation.longitude;

    // Apple Maps dirflg: d=driving, w=walking, r=transit.
    const appleDirflg =
      selectedMode === "walk" ? "w" : selectedMode === "drive" ? "d" : "r";

    // Google's universal web URL travelmode param.
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

  // Shared by the map marker callout and the venue bottom sheet's
  // VerificationCard — both confirm/resolve against the same report.
  // Like report submission, confirm/resolve requires a real login
  // server-side (require_bearer_auth on POST /reports/{id}/confirmations)
  // — a guest browsing the map can view reports but not act on them, same
  // as they can't submit one.
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

      // Re-fetch rather than patch local state — confirmation counts,
      // status, and expiry are all server-derived.
      await refreshReports();
    },
    [isAuthenticated],
  );

  // Optimistic — flips the heart immediately rather than waiting on the
  // network, then rolls back only if the request actually fails. Same
  // login-gate pattern as report confirmation, since both require
  // require_bearer_auth server-side.
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

  // Fetch-on-filter-change. This is the standard "synchronize with an
  // external system" effect use case (re-fetch venues/reports whenever the
  // active filters change) — exactly what useEffect is for. The lint rule
  // flags it anyway because loadData sets loading state before its first
  // await; that's the correct/expected shape for a fetch-triggered loading
  // indicator, not an anti-pattern, so it's disabled here rather than
  // restructured.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-dependency-change
    loadData();
  }, [loadData]);

  const filteredVenues = useMemo(() => {
    return venues.filter((venue) => {
      const matchesSearch = venue.name
        .toLowerCase()
        .includes(search.toLowerCase());

      // undefined liveStatus (no chip selected) means "don't filter by
      // this at all" — matches everything. Once a chip IS selected,
      // venues whose busyness hasn't been fetched yet are deliberately
      // excluded rather than shown anyway, since we genuinely don't
      // know their status yet. Since venues state updates progressively
      // as the busyness-fetch effect below resolves each request, this
      // list fills in as real data arrives rather than staying
      // permanently incomplete.
      const matchesLiveStatus =
        !liveStatus || venue.busyness?.busyness_status === liveStatus;

      return (
        matchesSearch && matchesCategory(venue, category) && matchesLiveStatus
      );
    });
  }, [venues, search, category, liveStatus]);

  // Fetches busyness for whichever venues currently match the selected
  // category (i.e. whatever's actually rendered as markers), merging the
  // result into venues state so VenueMarker's existing colour-mapping
  // logic — which already correctly reads venue.busyness?.busyness_color
  // — actually has real data to read. That logic was already built and
  // correct; it was just never being fed anything, since the main
  // /venues list endpoint never embeds busyness data at all (confirmed
  // directly against venues.py).
  //
  // Deliberately scoped to the current category, not the full venues
  // array — getVenues() has no venue_type filter at all, so venues state
  // holds every type at once (~4,800), and fetching busyness for all of
  // that on every load would be genuinely excessive. Scoping to category
  // keeps this to whatever's actually visible, typically a few hundred
  // at most.
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

  // Region tracking + a ref to the MapView itself — both needed for the
  // zoom in/out buttons below, which work by nudging the current
  // region's lat/lng "delta" (how much area is visible) and animating
  // to it, rather than using any platform-specific zoom API directly.
  const mapRef = useRef<MapView>(null);

  const [region, setRegion] = useState(INITIAL_REGION);

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

        {/* Route line — draws once a route has been selected via
            RouteOptionsModal/RouteDetailModal, and stays visible even
            after RouteDetailModal is closed (so the route stays on the
            map while navigating), until a different route is selected. */}

        {routeDetail?.polyline_preview &&
          routeDetail.polyline_preview.length > 0 && (
            <Polyline
              coordinates={routeDetail.polyline_preview}
              strokeColor={Colours.primary}
              strokeWidth={4}
            />
          )}
      </MapView>

      {/* ---------------------- Top Overlay ---------------------- */}

      <View style={styles.topOverlay}>
        <MapSearchBar
          value={search}
          onChangeText={setSearch}
          onFilterPress={() => setFilterVisible(true)}
        />

        <CategoryChips selected={category} onSelect={setCategory} />
      </View>

      {/* ---------------------- Zoom Controls ---------------------- */}

      <View style={styles.zoomControls}>
        <TouchableOpacity style={styles.zoomButton} onPress={handleZoomIn}>
          <Ionicons name="add" size={24} color={Colours.text} />
        </TouchableOpacity>

        <View style={styles.zoomDivider} />

        <TouchableOpacity style={styles.zoomButton} onPress={handleZoomOut}>
          <Ionicons name="remove" size={24} color={Colours.text} />
        </TouchableOpacity>
      </View>

      {/* ---------------------- Floating Buttons ---------------------- */}

      <FloatingActionButtons
        onSOSPress={() => router.push("/sos")}
        onReportPress={() => setReportVisible(true)}
      />

      {/* Only rendered while a route polyline is actually on screen — the
          line otherwise has no way to be dismissed once set, short of
          picking a different route to overwrite it. */}

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

      {/* ---------------------- Filters ---------------------- */}

      <FilterModal
        visible={filterVisible}
        openNow={openNow}
        accessible={accessible}
        language={language}
        autoCurrentTime={autoCurrentTime}
        onClose={() => setFilterVisible(false)}
        onApply={(filters) => {
          setOpenNow(filters.openNow);

          setAccessible(filters.accessible);

          setLanguage(filters.language);

          setAutoCurrentTime(filters.autoCurrentTime);

          setLiveStatus(filters.liveStatus);

          setTimeOffset(filters.timeOffset);
        }}
      />

      {/* ---------------------- Report Modal ---------------------- */}

      <ReportModal
        visible={reportVisible}
        onClose={() => setReportVisible(false)}
        isAuthenticated={isAuthenticated}
        locationEnabled={locationEnabled}
        currentLocation={currentLocation}
        nearbyVenues={venues}
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

      {/* ---------------------- Venue Sheet ---------------------- */}

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

      {/* ---------------------- Report Sheet ---------------------- */}

      <ReportBottomSheet
        visible={reportSheetVisible}
        report={selectedReport}
        onClose={() => setReportSheetVisible(false)}
        onConfirm={(reportId) =>
          handleReportConfirmation(reportId, "still_here")
        }
        onResolve={(reportId) => handleReportConfirmation(reportId, "resolved")}
      />

      {/* ---------------------- Route Options Modal ---------------------- */}

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

      {/* ---------------------- Route Details Modal ---------------------- */}

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

  // Positioned on the right side, vertically roughly mid-screen — clear
  // of the topOverlay (search + category chips) above and
  // FloatingActionButtons (SOS + Report, bottom-right) below.
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
});

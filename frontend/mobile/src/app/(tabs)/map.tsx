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

// Shared by filteredVenues and the busyness-fetching effect below — both
// need the same "which venues match the selected category" logic.
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

// Mirrors the exact colours VenueMarker paints markers with (the
// COLOURS map in VenueMarker.tsx)
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
  // Matches VenueMarker's getMarkerColour() fallback (COLOURS.blue) — hit
  // whenever busyness_color isn't green/yellow/red, i.e. no busyness data
  // fetched yet for that venue.
  {
    translationKey: "map.filters.unknown",
    defaultValue: "Unknown",
    colour: "#2563EB",
  },
] as const;

export default function MapScreen() {
  const { t } = useTranslation();

  // Full venue + report lists as loaded from the API, before any local
  // search/category/filter narrowing is applied.
  const [venues, setVenues] = useState<Venue[]>([]);

  const [reports, setReports] = useState<Report[]>([]);

  const [loading, setLoading] = useState(true);

  // Search text and selected category chip — both drive filteredVenues
  // below.
  const [search, setSearch] = useState("");

  const [category, setCategory] = useState<Category>("Clinic");

  // Which venue's marker was tapped (or picked from search), and the
  // bottom sheet visibility that goes with it.
  const [selectedVenueId, setSelectedVenueId] = useState<string | null>(null);

  const selectedVenue = useMemo(
    () => venues.find((v) => v.venue_id === selectedVenueId) ?? null,
    [venues, selectedVenueId],
  );

  // The single active (unresolved) report tied to the selected venue, if
  // any, used to populate VerificationCard in the venue sheet.
  const activeReportForSelectedVenue = useMemo(() => {
    if (!selectedVenueId) return null;

    return (
      reports.find(
        (r) => r.venue_id === selectedVenueId && r.status === "active",
      ) ?? null
    );
  }, [reports, selectedVenueId]);

  const [venueVisible, setVenueVisible] = useState(false);

  // Same pattern as the venue sheet above, but for a tapped report
  // marker.
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const selectedReport = useMemo(
    () => reports.find((r) => r.report_id === selectedReportId) ?? null,
    [reports, selectedReportId],
  );

  const [reportSheetVisible, setReportSheetVisible] = useState(false);

  // Visibility flags for the various modals/sheets this screen owns.
  const [filterVisible, setFilterVisible] = useState(false);

  const [reportVisible, setReportVisible] = useState(false);

  const [loginModalVisible, setLoginModalVisible] = useState(false);

  // Active filter values, all set via FilterModal's onApply.
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

  // Directions/route flow state — options list, the chosen route's
  // detail, and the two modals that display them in sequence.
  const [routeOptionsVisible, setRouteOptionsVisible] = useState(false);

  const [routeDetailVisible, setRouteDetailVisible] = useState(false);

  const [locationModalVisible, setLocationModalVisible] = useState(false);

  const [selectedMode, setSelectedMode] = useState("walk");

  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);

  const [routeDetail, setRouteDetail] = useState<RouteDetail | null>(null);

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
  // also leaves that undefined.
  const [busynessFetchedIds, setBusynessFetchedIds] = useState<Set<string>>(
    new Set(),
  );

  const [locationEnabled, setLocationEnabled] = useState(false);

  const [currentLocation, setCurrentLocation] = useState(DEFAULT_LOCATION);

  // Region tracking + a ref to the MapView itself — both needed for the
  // zoom in/out buttons below, which work by nudging the current
  // region's lat/lng "delta" (how much area is visible) and animating
  // to it, rather than using any platform-specific zoom API directly.
  const mapRef = useRef<MapView>(null);

  const [region, setRegion] = useState(INITIAL_REGION);

  // ---------------------------------------------------------------------
  // Auth + device location
  // ---------------------------------------------------------------------

  // Checks once on mount whether a token exists, to know whether to
  // treat the user as logged in or a guest.
  useEffect(() => {
    (async () => {
      const token = await getAccessToken();
      setIsAuthenticated(!!token);
    })();
  }, []);

  // Favourites require a real login.
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

  // Requests location permission and grabs an initial fix on mount, so
  // the map/report flows have a real starting position rather than the
  // hardcoded DEFAULT_LOCATION.
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
  }, [openNow, language]);

  // Re-fetches just the reports list, used after any action that changes
  // report state (submitting, confirming, resolving) without needing a
  // full venues reload too.
  async function refreshReports() {
    try {
      const reportData = await getReports();
      setReports(reportData);
    } catch (error) {
      console.error(error);
    }
  }

  // Kicks off the directions flow for the selected venue: confirms
  // location is available, fetches route options for walk/transit/drive,
  // and opens RouteOptionsModal.
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

  // Called when the user picks a mode/route from RouteOptionsModal —
  // fetches the turn-by-turn detail for that mode and opens
  // RouteDetailModal.
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
  // guidance) — more realistic for language as it will be native. Apple
  // Maps on iOS since it's always installed with no extra dependency;
  // Google's cross-platform web URL as a universal fallback (opens the
  // Google Maps app if installed, otherwise a browser).
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
  // server-side (require_bearer_auth on POST /reports/{id}/confirmations).
  // A guest browsing the map can view reports but not act on them, same
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

  // Flips the heart immediately rather than waiting on the
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

  // Selecting a search suggestion: clears the search text (so the
  // dropdown closes), opens that venue's own detail sheet — same as
  // tapping its marker directly would — and recenters/zooms the map on
  // it via the same mapRef used by the zoom controls.
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

  // Fetch-on-filter-change. This is the standard "synchronize with an
  // external system" effect use case (re-fetch venues/reports whenever the
  // active filters change).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-dependency-change
    loadData();
  }, [loadData]);

  // Applies the search text, category chip, live-status, and wheelchair
  // filters together — this is what actually drives which markers render
  // on the map.
  const filteredVenues = useMemo(() => {
    return venues.filter((venue) => {
      const matchesSearch = venue.name
        .toLowerCase()
        .includes(search.toLowerCase());

      // undefined liveStatus (no chip selected) means "don't filter by
      // this at all" — matches everything. Once a chip IS selected,
      // venues whose busyness hasn't been fetched yet are deliberately
      // excluded rather than shown anyway.
      // permanently incomplete.
      const matchesLiveStatus =
        !liveStatus || venue.busyness?.busyness_status === liveStatus;

      // "full_access" only matches venues confirmed fully accessible.
      // "partial_or_full" is the broader option, matching either real
      // positive status.
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

  // Dropdown suggestions shown under the search bar, distinct from
  // filteredVenues (which drives the actual map markers).
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

  // Report venue picker should show nearby options, not every venue in
  // the dataset. Sorted by actual distance from the user's location via the
  // calculateDistance() Haversine helper, capped at 5.
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

  // Fetches busyness for whichever venues currently match the selected
  // category (i.e. whatever's actually rendered as markers), merging the
  // result into venues state so VenueMarker's existing colour-mapping
  // logic — which already correctly reads venue.busyness?.busyness_color
  // — actually has real data to read.
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

  // Halves the visible region delta (zooms in) and animates to it.
  const handleZoomIn = () => {
    const nextRegion = {
      ...region,
      latitudeDelta: region.latitudeDelta / 2,
      longitudeDelta: region.longitudeDelta / 2,
    };

    mapRef.current?.animateToRegion(nextRegion, 300);
  };

  // Doubles the visible region delta (zooms out) and animates to it.
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
          suggestions={searchSuggestions}
          onSelectSuggestion={handleSelectSearchSuggestion}
        />

        <CategoryChips selected={category} onSelect={setCategory} />
      </View>

      {/* ---------------------- Zoom Controls ---------------------- */}

      <View style={styles.zoomControls}>
        <TouchableOpacity
          accessibilityLabel="Zoom in"
          style={styles.zoomButton}
          onPress={handleZoomIn}
        >
          <Ionicons name="add" size={24} color={Colours.text} />
        </TouchableOpacity>

        <View style={styles.zoomDivider} />

        <TouchableOpacity
          accessibilityLabel="Zoom out"
          style={styles.zoomButton}
          onPress={handleZoomOut}
        >
          <Ionicons name="remove" size={24} color={Colours.text} />
        </TouchableOpacity>
      </View>

      {/* ---------------------- Busyness Legend ---------------------- */}

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

      {/* ---------------------- Floating Buttons ---------------------- */}

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

      {/* ---------------------- Filters ---------------------- */}

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

      {/* ---------------------- Report Modal ---------------------- */}

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

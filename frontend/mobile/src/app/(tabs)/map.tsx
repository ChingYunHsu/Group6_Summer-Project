import * as Location from "expo-location";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, StatusBar, StyleSheet, View } from "react-native";
import MapView, { Polyline } from "react-native-maps";
import { SafeAreaView } from "react-native-safe-area-context";
import CategoryChips, { Category } from "../../components/CategoryChips";
import FilterModal from "../../components/FilterModal";
import FloatingActionButtons from "../../components/FloatingActionButtons";
import LocationRequiredModal from "../../components/LocationRequiredModal";
import LoginRequiredModal from "../../components/LoginRequiredModal";
import MapSearchBar from "../../components/MapSearchBar";
import ReportMarker from "../../components/ReportMarker";
import ReportModal from "../../components/ReportModal";
import RouteDetailModal from "../../components/RouteDetailModal";
import RouteOptionsModal from "../../components/RouteOptionsModal";
import VenueBottomSheet from "../../components/VenueBottomSheet";
import VenueMarker from "../../components/VenueMarker";
import { Colours } from "../../constants/colours";
import { getAccessToken } from "../../services/authService";
import {
  confirmReport,
  getReports,
  getRouteDetail,
  getRouteOptions,
  getVenues,
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

// Fallback only — used until a real device location comes back, or if the
// user denies permission. Centre of Manhattan, matches INITIAL_REGION.
// (Previously this was hardcoded to a Dublin coordinate — presumably a dev
// leftover, not intentional for a Manhattan-focused app.)
const DEFAULT_LOCATION = {
  latitude: INITIAL_REGION.latitude,
  longitude: INITIAL_REGION.longitude,
};

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

  // Retained for FilterModal's onApply payload — not read directly in this
  // file's render path, but still part of the filter state passed down.
  const [, setLiveStatus] = useState<"quiet" | "moderate" | "busy">("moderate");

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

    setVenueVisible(false);

    try {
      const response = await getRouteOptions(
        selectedVenue?.venue_id,
        currentLocation,
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

      let matchesCategory = false;

      switch (category) {
        case "Clinic":
          matchesCategory = venue.venue_type === "clinic";
          break;

        case "Pharmacy":
          matchesCategory = venue.venue_type === "pharmacy";
          break;

        case "AED":
          matchesCategory = venue.venue_type === "emergencyasset";
          break;

        case "Hospital":
          matchesCategory = venue.venue_type === "hospital";
          break;

        case "Restroom":
          matchesCategory = venue.venue_type === "restroom";
          break;
      }

      return matchesSearch && matchesCategory;
    });
  }, [venues, search, category]);

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
        style={StyleSheet.absoluteFill}
        initialRegion={INITIAL_REGION}
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
            onConfirm={(reportId) =>
              handleReportConfirmation(reportId, "still_here")
            }
            onResolve={(reportId) =>
              handleReportConfirmation(reportId, "resolved")
            }
          />
        ))}

        {/* Route line — draws once a route has been selected via
            RouteOptionsModal/RouteDetailModal, and stays visible even
            after RouteDetailModal is closed (so the route stays on the
            map while navigating), until a different route is selected.
            NOTE: /routes/detail is still fully static server-side — this
            will draw *a* line correctly, but it's always the same fixed
            three-point path regardless of which venue was actually
            selected, until the backend stops hardcoding the response. */}

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

      {/* ---------------------- Floating Buttons ---------------------- */}

      <FloatingActionButtons
        onSOSPress={() => router.push("/sos")}
        onReportPress={() => setReportVisible(true)}
      />

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
          } catch (error) {
            console.error(error);
          }

          // Optimistic local flag so the marker reflects the warning
          // immediately; the refreshReports() call below replaces this
          // with server truth once it lands.
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
        onClose={() => setVenueVisible(false)}
        onDirectionsPress={handleDirections}
        onConfirmReport={(reportId) =>
          handleReportConfirmation(reportId, "still_here")
        }
        onResolveReport={(reportId) =>
          handleReportConfirmation(reportId, "resolved")
        }
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
        onStartNavigation={() => {
          console.log("Navigation Started");
          setRouteDetailVisible(false);
        }}
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
});

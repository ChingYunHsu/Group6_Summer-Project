import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ActivityIndicator,
  StatusBar,
  StyleSheet,
  View,
} from "react-native";

import { SafeAreaView } from "react-native-safe-area-context";

import MapView from "react-native-maps";

import { router } from "expo-router";

import { Colours } from "../constants/colours";

import {
  getReports,
  getVenues,
} from "../services/api";

import {
  Report,
  Venue,
} from "../types/venue";

import CategoryChips, {
  Category,
} from "../components/CategoryChips";

import FilterModal from "../components/FilterModal";

import FloatingActionButtons from "../components/FloatingActionButtons";

import MapSearchBar from "../components/MapSearchBar";

import ReportMarker from "../components/ReportMarker";

import ReportModal from "../components/ReportModal";

import VenueBottomSheet from "../components/VenueBottomSheet";

import VenueMarker from "../components/VenueMarker";

const INITIAL_REGION = {
  latitude: 40.758,
  longitude: -73.9855,
  latitudeDelta: 0.08,
  longitudeDelta: 0.08,
};

export default function MapScreen() {
  const [venues, setVenues] =
    useState<Venue[]>([]);

  const [reports, setReports] =
    useState<Report[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [search, setSearch] =
    useState("");

  const [category, setCategory] =
    useState<Category>("Clinic");

  const [selectedVenueId, setSelectedVenueId] = useState<string | null>(null);

const selectedVenue = useMemo(
  () => venues.find(v => v.venue_id === selectedVenueId) ?? null,
  [venues, selectedVenueId]
);

  const [
    venueVisible,
    setVenueVisible,
  ] =
    useState(false);

  const [
    filterVisible,
    setFilterVisible,
  ] =
    useState(false);

  const [
    reportVisible,
    setReportVisible,
  ] =
    useState(false);

  const [openNow, setOpenNow] =
    useState(false);

  const [
    accessible,
    setAccessible,
  ] =
    useState(false);

  const [language, setLanguage] =
    useState("");

  const [autoCurrentTime, setAutoCurrentTime] =
  useState(true);

const [liveStatus, setLiveStatus] =
  useState<
    "quiet" | "moderate" | "busy"
  >("moderate");

  async function loadData() {
    try {
      setLoading(true);

      const [
        venueData,
        reportData,
      ] = await Promise.all([
        getVenues({
          open_now: openNow,
          accessible,
          languages: language
            ? [language]
            : [],
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
  }

  useEffect(() => {
    loadData();
  }, [
    openNow,
    accessible,
    language,
  ]);

  const filteredVenues =
    useMemo(() => {
      return venues.filter(
        (venue) => {
          const matchesSearch =
            venue.name
              .toLowerCase()
              .includes(
                search.toLowerCase()
              );

          let matchesCategory =
            false;

          switch (category) {
            case "Clinic":
              matchesCategory =
                venue.venue_type ===
                "clinic";
              break;

            case "Pharmacy":
              matchesCategory =
                venue.venue_type ===
                "pharmacy";
              break;

            case "AED":
              matchesCategory =
                venue.venue_type ===
                "emergencyasset";
              break;
          }

          return (
            matchesSearch &&
            matchesCategory
          );
        }
      );
    }, [
      venues,
      search,
      category,
    ]);

  if (loading) {
    return (
      <SafeAreaView
        style={styles.loader}
      >
        <ActivityIndicator
          size="large"
          color={Colours.primary}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={styles.container}
    >
      <StatusBar
        barStyle="dark-content"
      />

      <MapView
        style={
          StyleSheet.absoluteFill
        }
        initialRegion={
          INITIAL_REGION
        }
        showsUserLocation
      >

              {filteredVenues.map((venue) => (
          <VenueMarker
    key={venue.venue_id}

    venue={venue}

    showLiveStatus={
        autoCurrentTime
    }

    onPress={() => setSelectedVenueId(venue.venue_id)}
/>
        ))}

        {reports.map((report) => (
          <ReportMarker
            key={report.report_id}
            report={report}
          />
        ))}

      </MapView>

      {/* ---------------------- Top Overlay ---------------------- */}

      <View style={styles.topOverlay}>

        <MapSearchBar
          value={search}
          onChangeText={setSearch}
          onFilterPress={() =>
            setFilterVisible(true)
          }
        />

        <CategoryChips
          selected={category}
          onSelect={setCategory}
        />

      </View>

      {/* ---------------------- Floating Buttons ---------------------- */}

      <FloatingActionButtons
        onSOSPress={() =>
          router.push("/sos")
        }
        onReportPress={() =>
          setReportVisible(true)
        }
      />

      {/* ---------------------- Filters ---------------------- */}

      <FilterModal
  visible={filterVisible}

  openNow={openNow}

  accessible={accessible}

  language={language}

  autoCurrentTime={autoCurrentTime}

  onClose={() =>
    setFilterVisible(false)
  }

  onApply={(filters) => {

    setOpenNow(filters.openNow);

    setAccessible(filters.accessible);

    setLanguage(filters.language);

    setAutoCurrentTime(
      filters.autoCurrentTime
    );

    setLiveStatus(
      filters.liveStatus
    );

  }}
/>

      {/* ---------------------- Report Modal ---------------------- */}

      <ReportModal
  visible={reportVisible}
  onClose={() => setReportVisible(false)}

  // TEMP VALUES
  isAuthenticated={true}
  locationEnabled={true}

  currentLocation={{
    latitude: 53.3498,
    longitude: -6.2603,
  }}

  nearbyVenues={venues}

  onRequireLogin={() => {
    console.log("Navigate to login");
  }}

  onRequireLocation={() => {
    console.log("Open location settings");
  }}

  onSubmitVenue={(report) => {
  setVenues(current =>
    current.map(venue => {
      if (venue.venue_id !== report.venueId) {
        return venue;
      }

      return {
        ...venue,

        active_warning: true,

        live_report_count:
          (venue.live_report_count ?? 0) + 1,
      };
    })
  );

  setReportVisible(false);
}}

  onSubmitIncident={(report) => {

  const incident: Report = {

    report_id: `local-${Date.now()}`,

    venue_id: undefined,
    venue_name: undefined,
    venue_category: undefined,

    issue_type: report.issueType,

    latitude: report.latitude,
    longitude: report.longitude,

    accuracy_m: 5,

    anonymous: true,

    description: report.description,

    photos: [],

    status: "active",

    created_at: report.timestamp,

    expires_at: new Date(
      Date.now() + 60 * 60 * 1000
    ).toISOString(),

    expires_in_minutes: 60,

    confirmations: {
      count: 0,
      latest_action: "",
      latest_action_at: report.timestamp,
    },

    badge_text: "New Report (local)",
  };

  setReports(current => [
    incident,
    ...current,
  ]);

  setReportVisible(false);
}}
/>

      {/* ---------------------- Venue Sheet ---------------------- */}

      <VenueBottomSheet
        visible={venueVisible}
        venue={selectedVenue}
        autoCurrentTime={autoCurrentTime}
        onClose={() =>
          setVenueVisible(false)
        }
      />

    </SafeAreaView>
  );

}

const styles = StyleSheet.create({

  container: {

    flex: 1,

    backgroundColor:
      Colours.background,

  },

  loader: {

    flex: 1,

    justifyContent: "center",

    alignItems: "center",

    backgroundColor:
      Colours.background,

  },

  topOverlay: {

    position: "absolute",

    top: 60,

    left: 20,

    right: 20,

  },

});
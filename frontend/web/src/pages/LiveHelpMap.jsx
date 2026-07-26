import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import "./LiveHelpMap.css";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useTranslation } from "react-i18next";
import ChatbotWidget from "../components/ChatbotWidget";
import i18n from "../i18n";


import {
  getRouteDetail,
  getRouteOptions,
  getVenueBusyness,
  getVenueBusynessForecast,
  getVenueById,
  listReports,
  listVenues,
} from "../services/LiveHelpMapApi";

import {
  addFavourite,
  deleteFavourite,
  listFavourites,
} from "../services/FavouritesApi";

const LANGUAGE_CODES = {
  "English (English)": "en",
  "Français (French)": "fr",
  "Español (Spanish)": "es",
  "中文 (Chinese)": "zh",
  "العربية (Arabic)": "ar",
};


function getFavouriteVenueId(favourite) {
  return (
    favourite?.venue_id ??
    favourite?.venueId ??
    favourite?.venue?.venue_id ??
    favourite?.venue?.id ??
    null
  );
}

function getMarkerColor(venue, futureMode) {
  if (futureMode) return "#0057e7";

  const providedColor = String(
    venue.busyness_color ?? venue.marker_color ?? ""
  )
    .trim()
    .toLowerCase();

  const colorMap = {
    green: "#22c55e",
    quiet: "#22c55e",
    low: "#22c55e",
    yellow: "#eab308",
    moderate: "#eab308",
    medium: "#eab308",
    red: "#ef4444",
    busy: "#ef4444",
    high: "#ef4444",
    blue: "#0057e7",
    unknown: "#0057e7",
  };

  if (providedColor in colorMap) {
    return colorMap[providedColor];
  }

  if (
    providedColor.startsWith("#") ||
    providedColor.startsWith("rgb") ||
    providedColor.startsWith("hsl")
  ) {
    return providedColor;
  }

  const rawPercent = venue.busyness_percent;

  const percent =
    rawPercent === null ||
    rawPercent === undefined ||
    rawPercent === ""
      ? Number.NaN
      : Number(rawPercent);
    
  if (Number.isFinite(percent)) {
    if (percent < 30) return "#22c55e";
    if (percent <= 70) return "#eab308";
    return "#ef4444";
  }

  const level = String(
    venue.busyness_level ?? venue.busyness_status ?? ""
  ).toLowerCase();

  if (level.includes("quiet") || level.includes("low")) {
    return "#22c55e";
  }

  if (
    level.includes("moderate") ||
    level.includes("medium")
  ) {
    return "#eab308";
  }

  if (
    level.includes("busy") ||
    level.includes("high") ||
    level.includes("capacity")
  ) {
    return "#ef4444";
  }

  return "#0057e7";
}

function getIcon(venue) {
  const type = String(
    venue?.venue_type ?? venue?.type ?? ""
  ).toLowerCase();

  if (venueIsPharmacy(venue)) return "⚕";
  if (venueIsHospital(venue)) return "🏥";
  if (type === "clinic" || type === "healthcare") return "✚";
  if (type === "aed" || type === "emergencyasset") return "❤️";
  if (type === "toilet" || type === "restroom") return "🚽";
  if (type === "hospital") return "🏥";

  return "●";
}

function getReportIcon(issueType) {
  if (issueType === "large_crowd" || issueType === "long_waiting_time") {
    return "⚠";
  }

  if (
    issueType === "elevator_broken" ||
    issueType === "wheelchair_lift_broken" ||
    issueType === "ramp_blocked"
  ) {
    return "♿";
  }

  return "ⓘ";
}

function isAccessibilityReport(issueType) {
  return ["elevator_broken", "wheelchair_lift_broken", "ramp_blocked"].includes(issueType);
}

const MOCK_USER_LOCATION = {
  lat: 40.758,
  lng: -73.9855,
};

/*
 * getIssueMessage is called from plain (non-component) normalisation
 * helpers, so it uses the shared i18next instance directly via i18n.t(...)
 * rather than the useTranslation hook, which is only available inside
 * React components.
 */
function getIssueMessage(issueType) {
  const messages = {
    elevator_broken: i18n.t("liveHelpMap.issueMessages.elevatorBroken"),
    wheelchair_lift_broken: i18n.t("liveHelpMap.issueMessages.wheelchairLiftBroken"),
    toilet_out_of_order: i18n.t("liveHelpMap.issueMessages.toiletOutOfOrder"),
    large_crowd: i18n.t("liveHelpMap.issueMessages.largeCrowd"),
    long_waiting_time: i18n.t("liveHelpMap.issueMessages.longWaitingTime"),
    protest_or_blockage: i18n.t("liveHelpMap.issueMessages.protestOrBlockage"),
    entrance_closed: i18n.t("liveHelpMap.issueMessages.entranceClosed"),
    ramp_blocked: i18n.t("liveHelpMap.issueMessages.rampBlocked"),
    closed_early: i18n.t("liveHelpMap.issueMessages.closedEarly"),
  };

  return messages[issueType] || i18n.t("liveHelpMap.activeCommunityReport");
}

function normaliseVenue(rawVenue) {
  const languages = normaliseList(
    rawVenue.language_tags ??
      rawVenue.languages
  ).map(normaliseLanguage);

  return {
    ...rawVenue,

    venue_id:
      rawVenue.venue_id ??
      rawVenue.id,

    latitude: Number(
      rawVenue.latitude ??
        rawVenue.lat
    ),

    longitude: Number(
      rawVenue.longitude ??
        rawVenue.lng
    ),

    venue_type: String(
      rawVenue.venue_type ??
        rawVenue.type ??
        ""
    ).toLowerCase(),

    language_tags: languages,

    supported_services: normaliseList(
      rawVenue.supported_services ??
        rawVenue.services
    ),
  };
}

function normaliseBusyness(payload) {
  const rawBusyness = payload?.busyness ?? payload ?? {};

  return {
    ...rawBusyness,

    busyness_percent:
      rawBusyness.busyness_percent ??
      rawBusyness.percent ??
      rawBusyness.load_percent ??
      null,

    busyness_level:
      rawBusyness.busyness_level ??
      rawBusyness.busyness_status ??
      rawBusyness.level ??
      rawBusyness.status ??
      "No Live Info",

    busyness_status:
      rawBusyness.busyness_status ??
      rawBusyness.status ??
      rawBusyness.busyness_level ??
      rawBusyness.level ??
      "unknown",

    busyness_color:
      rawBusyness.busyness_color ??
      rawBusyness.color ??
      null,

    avg_wait_minutes:
      rawBusyness.avg_wait_minutes ??
      rawBusyness.estimated_wait_minutes ??
      null,
  };
}

function normaliseForecast(rawForecast) {
  const points =
    rawForecast.busyness_forecast_12h ??
    rawForecast.forecast ??
    rawForecast.points ??
    rawForecast.items ??
    [];

  return Array.isArray(points)
    ? points.map((point, index) => ({
        ...point,
        offset_hours: point.offset_hours ?? point.hour_offset ?? index,
        percent:
          point.percent ??
          point.busyness_percent ??
          point.load_percent ??
          0,
        level:
          point.level ??
          point.busyness_level ??
          point.status ??
          "Unknown",
      }))
    : [];
}

function getConfirmationCount(rawReport) {
  const confirmations = rawReport.confirmations;

  if (typeof confirmations === "number") {
    return confirmations;
  }

  if (Array.isArray(confirmations)) {
    return confirmations.length;
  }

  if (
    confirmations &&
    typeof confirmations === "object"
  ) {
    const count = Number(confirmations.count);
    return Number.isFinite(count) ? count : 0;
  }

  const fallbackCount = Number(
    rawReport.confirmation_count ??
      rawReport.confirmed_count ??
      0
  );

  return Number.isFinite(fallbackCount)
    ? fallbackCount
    : 0;
}

function normaliseReport(rawReport) {
  return {
    ...rawReport,

    report_id:
      rawReport.report_id ??
      rawReport.id,

    message:
      rawReport.message ??
      rawReport.description ??
      getIssueMessage(rawReport.issue_type),

    confirmations: getConfirmationCount(rawReport),

    confirmation_summary:
      rawReport.confirmations &&
      typeof rawReport.confirmations === "object" &&
      !Array.isArray(rawReport.confirmations)
        ? rawReport.confirmations
        : null,

    icon:
      rawReport.icon ??
      getReportIcon(rawReport.issue_type),
  };
}

const TRAVEL_MODE_UI = {
  walk: {
    labelKey: "liveHelpMap.routePlanner.walking",
    routeLabelKey: "liveHelpMap.routePlanner.walkingRoute",
    icon: "🚶",
  },
  transit: {
    labelKey: "liveHelpMap.routePlanner.transit",
    routeLabelKey: "liveHelpMap.routePlanner.transitRoute",
    icon: "🚇",
  },
  drive: {
    labelKey: "liveHelpMap.routePlanner.driving",
    routeLabelKey: "liveHelpMap.routePlanner.drivingRoute",
    icon: "🚗",
  },
};

function normaliseRouteOptions(payload) {
  const providedOptions = Array.isArray(payload?.options)
    ? payload.options
    : [];

  if (providedOptions.length > 0) {
    return providedOptions
      .map((option) => ({
        ...option,
        mode: String(option?.mode ?? "").toLowerCase(),
        duration_minutes: Number(option?.duration_minutes),
      }))
      .filter((option) => option.mode in TRAVEL_MODE_UI);
  }

  const summaryByMode = payload?.summary_by_mode;

  if (!summaryByMode || typeof summaryByMode !== "object") {
    return [];
  }

  return Object.entries(summaryByMode)
    .map(([mode, summary]) => ({
      ...(summary ?? {}),
      mode: String(mode).toLowerCase(),
      duration_minutes: Number(summary?.duration_minutes),
      summary: `${i18n.t(TRAVEL_MODE_UI[mode]?.labelKey) ?? mode} route`,
    }))
    .filter((option) => option.mode in TRAVEL_MODE_UI);
}

function normaliseRouteCoordinate(point) {
  if (Array.isArray(point)) {
    const latitude = Number(point[0]);
    const longitude = Number(point[1]);
    return [longitude, latitude];
  }

  const latitude = Number(point?.lat ?? point?.latitude);
  const longitude = Number(
    point?.lng ?? point?.lon ?? point?.longitude
  );

  return [longitude, latitude];
}

function formatRouteStatus(value) {
  if (!value) return i18n.t("venueSheet.unknown", { defaultValue: "Status unavailable" });

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function removeRouteLayer(map) {
  if (!map) return;

  if (map.getLayer("active-route-line")) {
    map.removeLayer("active-route-line");
  }

  if (map.getSource("active-route")) {
    map.removeSource("active-route");
  }
}

function buildQueryTime(selectedDate, selectedTime) {
  if (!selectedDate || !selectedTime) return "";

  // The API requires an ISO-8601 date-time. This preserves the selected
  // wall-clock value. Confirm with the backend whether it should be treated
  // as Manhattan time or converted to UTC.
  return `${selectedDate}T${selectedTime}:00`;
}

const LANGUAGE_ALIASES = {
  en: "en",
  english: "en",

  fr: "fr",
  french: "fr",
  français: "fr",

  es: "es",
  spanish: "es",
  español: "es",

  zh: "zh",
  chinese: "zh",
  中文: "zh",

  ar: "ar",
  arabic: "ar",
  العربية: "ar",
};

function normaliseList(value) {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);

      if (Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      return value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return [];
}

function normaliseLanguage(value) {
  const cleanedValue = String(value)
    .trim()
    .toLowerCase();

  return LANGUAGE_ALIASES[cleanedValue] ?? cleanedValue;
}

const PHARMACY_TERMS = [
  "pharmacy",
  "chemist",
  "drugstore",
  "drug store",
];

function venueIsPharmacy(venue) {
  // This checks all available venue fields, including subtype,
  // category and amenity fields that may not be displayed.
  const searchableVenue = JSON.stringify(venue ?? {}).toLowerCase();

  return PHARMACY_TERMS.some((term) =>
    searchableVenue.includes(term)
  );
}

function venueMatchesCategory(venue, selectedType) {
  if (!selectedType) return true;

  const venueType = String(
    venue.venue_type ?? venue.type ?? ""
  ).toLowerCase();

  if (selectedType === "pharmacy") {
    return venueIsPharmacy(venue);
  }

  if (selectedType === "hospital") {
    return venueIsHospital(venue);
  }

  if (selectedType === "clinic") {
    return (
      ["clinic", "healthcare"].includes(venueType) &&
      !venueIsPharmacy(venue)
    );
  }

  if (selectedType === "emergencyasset") {
    return ["emergencyasset", "aed"].includes(venueType);
  }

  if (selectedType === "restroom") {
    return ["restroom", "toilet"].includes(venueType);
  }

  return venueType === selectedType;
}

function venueIsAccessible(venue) {
  const value =
    venue.accessible ??
    venue.wheelchair_accessible ??
    venue.accessible_status ??
    "";

  if (typeof value === "boolean") {
    return value;
  }

  const cleanedValue = String(value).toLowerCase();

  return (
    cleanedValue === "true" ||
    cleanedValue === "yes" ||
    cleanedValue.includes("full") ||
    cleanedValue.includes("accessible")
  );
}

const HOSPITAL_TERMS = [
  "hospital",
  "medical center",
  "medical centre",
  "infirmary",
  "emergency room",
];

function venueIsHospital(venue) {
  const venueType = String(
    venue?.venue_type ?? venue?.type ?? ""
  ).toLowerCase();

  // Prevent hospital-named AED records from appearing as hospitals.
  if (!["healthcare", "hospital"].includes(venueType)) {
    return false;
  }

  const searchableText = [
    venue?.name,
    venue?.category,
    venue?.subtype,
    venue?.amenity,
    venue?.healthcare,
    venue?.description,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return HOSPITAL_TERMS.some((term) =>
    searchableText.includes(term)
  );
}

function LiveHelpMap() {
  const { t } = useTranslation("common");
  const BUSYNESS_BATCH_SIZE = 100;
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const userMarkerRef = useRef(null);

  const [venues, setVenues] = useState([]);
  const [venueDetailsById, setVenueDetailsById] = useState({});
  const [busynessByVenueId, setBusynessByVenueId] = useState({});
  const [forecastByVenueId, setForecastByVenueId] = useState({});
  const [liveReports, setLiveReports] = useState([]);
  const [busynessFetchedIds, setBusynessFetchedIds] = useState(
    () => new Set()
  );

  const [isLoading, setIsLoading] = useState(true);
  const [mapError, setMapError] = useState("");

  const [showFilters, setShowFilters] = useState(false);
  const [showLeftDrawer, setShowLeftDrawer] = useState(false);
  const [autoCurrentTime, setAutoCurrentTime] = useState(true);
  const [selectedTime, setSelectedTime] = useState("");
  const [selectedDate, setSelectedDate] = useState("");

  const [searchText, setSearchText] = useState("");
  const [primaryLanguage, setPrimaryLanguage] =
    useState("");
  const [secondaryLanguage, setSecondaryLanguage] = useState("None");
  const [accessibleOnly, setAccessibleOnly] = useState(false);
  const [selectedBusynessLevels, setSelectedBusynessLevels] = useState([]);
  const [appliedFilters, setAppliedFilters] = useState({
    languages: [],
    accessible: false,
    venueType: "clinic",
  });

  const [showRoutePlanner, setShowRoutePlanner] = useState(false);
  const [routeStart, setRouteStart] = useState("");
  const [routeDestination, setRouteDestination] = useState("");
  const [routeDepartureTime, setRouteDepartureTime] = useState("");
  const [selectedTravelMode, setSelectedTravelMode] = useState("walk");
  const [routeOptions, setRouteOptions] = useState([]);
  const [routeDetail, setRouteDetail] = useState(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState("");
  const [selectedVenueId, setSelectedVenueId] = useState(null);

  const [favouriteVenueIds, setFavouriteVenueIds] = useState([]);
  const [favouriteError, setFavouriteError] = useState("");
  const [updatingFavouriteId, setUpdatingFavouriteId] =
    useState(null);

  const futureMode = !autoCurrentTime;
  const queryTime = futureMode
    ? buildQueryTime(selectedDate, selectedTime)
    : "";

  const [userLocation] = useState({
    ...MOCK_USER_LOCATION,
    isMock: true,
  });

  const loadVenues = useCallback(async () => {
    try {
      setIsLoading(true);
      setMapError("");

      const backendVenues = await listVenues();
      const normalisedVenues = backendVenues
        .map(normaliseVenue)
        .filter(
          (venue) =>
            venue.venue_id &&
            Number.isFinite(venue.latitude) &&
            Number.isFinite(venue.longitude)
        );

      setVenues(normalisedVenues);

      setSelectedVenueId((currentId) => {
        if (
          currentId &&
          normalisedVenues.some((venue) => venue.venue_id === currentId)
        ) {
          return currentId;
        }

        return normalisedVenues[0]?.venue_id ?? null;
      });

      setShowLeftDrawer(normalisedVenues.length > 0);
    } catch (error) {
      console.error("Failed to load venues:", error);
      setMapError(error.message || t("liveHelpMap.couldNotLoadVenues"));
      setVenues([]);
      setSelectedVenueId(null);
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  const refreshReports = useCallback(async () => {
    try {
      const reports = await listReports({ status: "active" });
      setLiveReports(reports.map(normaliseReport));
    } catch (error) {
      console.error("Failed to load live reports:", error);
      setMapError((current) => current || error.message);
    }
  }, []);

  useEffect(() => {
    loadVenues();
  }, [loadVenues]);

  useEffect(() => {
    let cancelled = false;

    async function loadSavedFavourites() {
      try {
        const favourites = await listFavourites();

        if (cancelled) return;

        const venueIds = favourites
          .map(getFavouriteVenueId)
          .filter(Boolean);

        setFavouriteVenueIds([...new Set(venueIds)]);
        setFavouriteError("");
      } catch (error) {
        if (cancelled) return;

        console.error("Failed to load favourites:", error);

        setFavouriteError(
          error.message ||
            t("liveHelpMap.couldNotLoadFavourites")
        );
      }
    }

    void loadSavedFavourites();

    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    refreshReports();

    const interval = window.setInterval(refreshReports, 30000);
    return () => window.clearInterval(interval);
  }, [refreshReports]);

useEffect(() => {
  const selectedType = appliedFilters.venueType;

  if (!selectedType) return;

  const typeAliases = {
    clinic: ["clinic", "healthcare"],
    pharmacy: ["pharmacy"],
    emergencyasset: ["emergencyasset", "aed"],
    restroom: ["restroom", "toilet"],
  };

  const acceptedTypes =
    typeAliases[selectedType] ?? [selectedType];

  const venuesNeedingBusyness = venues
    .filter((venue) => {
      const venueType = String(
        venue.venue_type ?? ""
      ).toLowerCase();

      return (
        acceptedTypes.includes(venueType) &&
        !busynessFetchedIds.has(venue.venue_id)
      );
    })
    .slice(0, BUSYNESS_BATCH_SIZE);

  if (venuesNeedingBusyness.length === 0) {
    return;
  }

  let cancelled = false;

  async function loadBusynessBatch() {
    const results = await Promise.allSettled(
      venuesNeedingBusyness.map(async (venue) => {
        const payload = await getVenueBusyness(
          venue.venue_id,
          queryTime
        );

        return {
          venueId: venue.venue_id,
          busyness: normaliseBusyness(
            payload?.busyness ?? payload
          ),
        };
      })
    );

    if (cancelled) return;

    setBusynessByVenueId((current) => {
      const next = { ...current };

      results.forEach((result) => {
        if (result.status !== "fulfilled") {
          return;
        }

        const { venueId, busyness } = result.value;
        next[venueId] = busyness;
      });

      return next;
    });

    setBusynessFetchedIds((current) => {
      const next = new Set(current);

      venuesNeedingBusyness.forEach((venue) => {
        next.add(venue.venue_id);
      });

      return next;
    });
  }

  void loadBusynessBatch();

  return () => {
    cancelled = true;
  };
}, [
  appliedFilters.venueType,
  busynessFetchedIds,
  queryTime,
  venues,
]);

useEffect(() => {
  setBusynessFetchedIds(new Set());
  setBusynessByVenueId({});
}, [queryTime]);

  useEffect(() => {
    if (!selectedVenueId) return;

    let cancelled = false;

    async function loadSelectedVenueData() {
      const listVenue = venues.find(
        (venue) => venue.venue_id === selectedVenueId
      );

      const [venueResult, forecastResult] =
        await Promise.allSettled([
          getVenueById(selectedVenueId),
          getVenueBusynessForecast(selectedVenueId),
        ]);

      if (cancelled) return;

      const detailedPayload =
        venueResult.status === "fulfilled"
          ? venueResult.value
          : null;

      if (detailedPayload) {
        setVenueDetailsById((current) => ({
          ...current,
          [selectedVenueId]:
            normaliseVenue(detailedPayload),
        }));
      } else {
        console.error(
          "Failed to load selected venue details:",
          venueResult.reason
        );
      }

      if (forecastResult.status === "fulfilled") {
        setForecastByVenueId((current) => ({
          ...current,
          [selectedVenueId]: normaliseForecast(
            forecastResult.value
          ),
        }));
        return;
      }

      // Some venue responses already include busyness_forecast_12h.
      // Preserve that data when the dedicated forecast route returns 404.
      const embeddedForecast = normaliseForecast(
        detailedPayload ?? listVenue ?? {}
      );

      setForecastByVenueId((current) => ({
        ...current,
        [selectedVenueId]: embeddedForecast,
      }));

      if (forecastResult.reason?.status !== 404) {
        console.error(
          "Failed to load selected venue forecast:",
          forecastResult.reason
        );
      }
    }

    loadSelectedVenueData();

    return () => {
      cancelled = true;
    };
  }, [selectedVenueId, venues]);

  useEffect(() => {
  if (mapRef.current) return;

  mapRef.current = new maplibregl.Map({
    container: mapContainerRef.current,
    style:
      "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    center: [-73.9857, 40.758],
    zoom: 12,
  });

  mapRef.current.addControl(
    new maplibregl.NavigationControl(),
    "bottom-right"
  );

  return () => {
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    userMarkerRef.current?.remove();
    userMarkerRef.current = null;

    mapRef.current?.remove();
    mapRef.current = null;
  };
}, []);


useEffect(() => {
  if (!mapRef.current || !userLocation) {
    return;
  }

  if (userMarkerRef.current) {
    userMarkerRef.current.remove();
  }

  const markerElement = document.createElement("div");
  markerElement.className = "user-location-marker";

  markerElement.title = userLocation.isMock
    ? t("liveHelpMap.userLocationMock")
    : t("liveHelpMap.userLocationCurrent");

  userMarkerRef.current = new maplibregl.Marker({
    element: markerElement,
    anchor: "center",
  })
    .setLngLat([
      userLocation.lng,
      userLocation.lat,
    ])
    .addTo(mapRef.current);

  return () => {
    userMarkerRef.current?.remove();
    userMarkerRef.current = null;
  };
}, [userLocation, t]);

  useEffect(() => {
    const map = mapRef.current;
    const polyline = routeDetail?.polyline_preview;

    if (!map) return;

    if (!showRoutePlanner || !Array.isArray(polyline)) {
      removeRouteLayer(map);
      return;
    }

    const coordinates = polyline
      .map(normaliseRouteCoordinate)
      .filter(
        ([longitude, latitude]) =>
          Number.isFinite(longitude) &&
          Number.isFinite(latitude)
      );

    if (coordinates.length < 2) {
      removeRouteLayer(map);
      return;
    }

    const routeGeoJson = {
      type: "Feature",
      properties: {
        mode: selectedTravelMode,
      },
      geometry: {
        type: "LineString",
        coordinates,
      },
    };

    function drawRoute() {
      const existingSource = map.getSource("active-route");

      if (existingSource) {
        existingSource.setData(routeGeoJson);
      } else {
        map.addSource("active-route", {
          type: "geojson",
          data: routeGeoJson,
        });
      }

      if (!map.getLayer("active-route-line")) {
        map.addLayer({
          id: "active-route-line",
          type: "line",
          source: "active-route",
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": "#0057e7",
            "line-width": 6,
            "line-opacity": 0.85,
          },
        });
      }

      const bounds = coordinates.reduce(
        (currentBounds, coordinate) =>
          currentBounds.extend(coordinate),
        new maplibregl.LngLatBounds(
          coordinates[0],
          coordinates[0]
        )
      );

      map.fitBounds(bounds, {
        padding: 100,
        maxZoom: 16,
        duration: 700,
      });
    }

    if (map.isStyleLoaded()) {
      drawRoute();
    } else {
      map.once("load", drawRoute);
    }

    return () => {
      map.off("load", drawRoute);
    };
  }, [routeDetail, selectedTravelMode, showRoutePlanner]);

  const venuesWithBusyness = useMemo(
    () =>
      venues.map((venue) => ({
        ...venue,
        ...(busynessByVenueId[venue.venue_id] ?? {}),
      })),
    [busynessByVenueId, venues]
  );

  const visibleVenues = useMemo(() => {
    const cleanedSearch = searchText
      .trim()
      .toLowerCase();

    const requestedLanguages =
      appliedFilters.languages.map(
        normaliseLanguage
      );

    return venuesWithBusyness.filter((venue) => {
      const matchesSearch =
        !cleanedSearch ||
        [
          venue.name,
          venue.address,
          venue.borough,
        ]
          .filter(Boolean)
          .some((value) =>
            String(value)
              .toLowerCase()
              .includes(cleanedSearch)
          );

      const venueLanguages =
        normaliseList(
          venue.language_tags
        ).map(normaliseLanguage);

      const matchesLanguages =
        requestedLanguages.length === 0 ||
        requestedLanguages.every(
          (language) =>
            venueLanguages.includes(language)
        );

      const matchesAccessibility =
        !appliedFilters.accessible ||
        venueIsAccessible(venue);

      const selectedType = appliedFilters.venueType;

      const matchesVenueType = venueMatchesCategory(
        venue,
        selectedType
      );

    const busynessLevel = String(
      venue.busyness_level ?? ""
    ).toLowerCase();

    const matchesBusyness =
      futureMode ||
      selectedBusynessLevels.length === 0 ||
      selectedBusynessLevels.some(
        (selectedLevel) =>
          busynessLevel.includes(
            selectedLevel
          )
      );

    return (
      matchesSearch &&
      matchesLanguages &&
      matchesAccessibility &&
      matchesVenueType &&
      matchesBusyness
    );
  });
}, [
  appliedFilters,
  futureMode,
  searchText,
  selectedBusynessLevels,
  venuesWithBusyness,
]);

useEffect(() => {
  console.log("MAP VENUE DEBUG", {
    totalVenuesFromApi: venues.length,
    venuesWithBusyness: Object.keys(busynessByVenueId).length,
    visibleVenues: visibleVenues.length,
    searchText,
    appliedFilters,
    selectedBusynessLevels,
    futureMode,
  });
}, [
  venues,
  busynessByVenueId,
  visibleVenues,
  searchText,
  appliedFilters,
  selectedBusynessLevels,
  futureMode,
]);

  const openVenueDrawer = useCallback((venue) => {
    setSelectedVenueId(venue.venue_id);
    setRouteDestination(venue.name ?? "");
    setShowRoutePlanner(false);
    setShowLeftDrawer(true);
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    visibleVenues.forEach((venue) => {
      const markerEl = document.createElement("button");
      markerEl.type = "button";
      markerEl.className = "venue-pin";
      markerEl.style.backgroundColor = getMarkerColor(
        venue,
        futureMode
      );
      markerEl.innerHTML = `<span>${getIcon(
        venue
      )}</span>`;
      markerEl.style.pointerEvents = "auto";
      markerEl.style.zIndex = "10";
      markerEl.setAttribute(
        "aria-label",
        t("liveHelpMap.openVenue", {
          name: venue.name || t("liveHelpMap.venue"),
        })
      );

      markerEl.addEventListener("mousedown", (event) => {
        event.stopPropagation();
        openVenueDrawer(venue);
      });

      const marker = new maplibregl.Marker({
        element: markerEl,
        anchor: "center",
      })
        .setLngLat([venue.longitude, venue.latitude])
        .addTo(mapRef.current);

      markersRef.current.push(marker);
    });
  }, [futureMode, openVenueDrawer, visibleVenues, t]);

  const selectedVenue = useMemo(() => {
    if (!selectedVenueId) return null;

    const listVenue = venues.find(
      (venue) => venue.venue_id === selectedVenueId
    );
    const detailedVenue =
      venueDetailsById[selectedVenueId];

    if (!listVenue && !detailedVenue) return null;

    const endpointForecast =
      forecastByVenueId[selectedVenueId] ?? [];

    const embeddedForecast = normaliseForecast({
      ...listVenue,
      ...detailedVenue,
    });

    return {
      ...listVenue,
      ...detailedVenue,
      ...(busynessByVenueId[selectedVenueId] ?? {}),
      busyness_forecast_12h:
        endpointForecast.length > 0
          ? endpointForecast
          : embeddedForecast,
    };
  }, [
    busynessByVenueId,
    forecastByVenueId,
    selectedVenueId,
    venueDetailsById,
    venues,
  ]);

  const selectedRouteOption = useMemo(
    () =>
      routeOptions.find(
        (option) => option.mode === selectedTravelMode
      ) ?? null,
    [routeOptions, selectedTravelMode]
  );

  async function loadRoute(venue, mode, refreshOptions = false) {
    if (!venue?.venue_id) return;

    try {
      setRouteLoading(true);
      setRouteError("");

      if (refreshOptions) {
        setRouteOptions([]);
      }

      setRouteDetail(null);

      if (refreshOptions) {
        const [optionsPayload, detailPayload] =
          await Promise.all([
            getRouteOptions(venue.venue_id, userLocation),
            getRouteDetail(
              venue.venue_id,
              userLocation,
              mode
            ),
          ]);

        setRouteOptions(normaliseRouteOptions(optionsPayload));
        setRouteDetail(detailPayload);
        return;
      }

      const detailPayload = await getRouteDetail(
        venue.venue_id,
        userLocation,
        mode
      );

      setRouteDetail(detailPayload);
    } catch (error) {
      console.error(`Failed to load ${mode} route:`, error);

      setRouteError(
        error.message || t("liveHelpMap.couldNotCalculateThisRoute")
      );
    } finally {
      setRouteLoading(false);
    }
  }

  async function handleTravelModeChange(mode) {
    if (
      !selectedVenue ||
      mode === selectedTravelMode ||
      routeLoading
    ) {
      return;
    }

    setSelectedTravelMode(mode);
    await loadRoute(selectedVenue, mode, false);
  }

  async function handleRouteSearch() {
    if (!selectedVenue || routeLoading) return;

    await loadRoute(
      selectedVenue,
      selectedTravelMode,
      true
    );
  }

  const selectedVenueReports = useMemo(
    () =>
      liveReports.filter(
        (report) =>
          String(report.venue_id ?? "") ===
          String(selectedVenueId ?? "")
      ),
    [liveReports, selectedVenueId]
  );

  const landmarkAlert = selectedVenueReports[0] ?? null;
  const selectedAccessibilityReports = selectedVenueReports.filter((report) =>
    isAccessibilityReport(report.issue_type)
  );
  const standaloneAlerts = liveReports.filter(
    (report) => !report.venue_id
  );

  function handleAdvancedFiltersClick() {
    setShowFilters(true);
  }

  async function handleSaveLocation() {
    if (!selectedVenue) return;

    const venueId =
      selectedVenue.venue_id ?? selectedVenue.id;

    if (!venueId) {
      setFavouriteError(t("liveHelpMap.invalidVenueId"));
      return;
    }

    const isAlreadyFavourite =
      favouriteVenueIds.includes(venueId);

    try {
      setUpdatingFavouriteId(venueId);
      setFavouriteError("");

      if (isAlreadyFavourite) {
        await deleteFavourite(venueId);

        setFavouriteVenueIds((currentIds) =>
          currentIds.filter((id) => id !== venueId)
        );
      } else {
        await addFavourite(venueId);

        setFavouriteVenueIds((currentIds) => [
          ...new Set([...currentIds, venueId]),
        ]);
      }

      window.dispatchEvent(
        new Event("clearpath:saved-locations-updated")
      );
    } catch (error) {
      console.error(
        "Failed to update favourite:",
        error
      );

      setFavouriteError(
        error.message ||
          t("liveHelpMap.couldNotUpdateFavourite")
      );
    } finally {
      setUpdatingFavouriteId(null);
    }
  }

  async function handleOpenLiveDirections() {
    if (!selectedVenue) return;

    setSelectedTravelMode("walk");
    setShowRoutePlanner(true);
    setShowLeftDrawer(false);
    setRouteStart(t("liveHelpMap.userLocationMock"));
    setRouteDestination(selectedVenue.name ?? t("liveHelpMap.venue"));
    setRouteDepartureTime(t("liveHelpMap.routePlanner.leaveNow"));

    await loadRoute(selectedVenue, "walk", true);
  }

  function closeRoutePlanner() {
    removeRouteLayer(mapRef.current);
    setRouteDetail(null);
    setRouteOptions([]);
    setRouteError("");
    setSelectedTravelMode("walk");
    setShowRoutePlanner(false);
    setShowLeftDrawer(true);
  }

  function applyFilters() {
  const languages = [
    LANGUAGE_CODES[primaryLanguage],
    secondaryLanguage === "None"
      ? null
      : LANGUAGE_CODES[secondaryLanguage],
  ].filter(Boolean);

  setAppliedFilters((current) => ({
    ...current,
    languages,
    accessible: accessibleOnly,
  }));

  setShowFilters(false);
}

  function clearFilters() {
    setPrimaryLanguage("");
    setSecondaryLanguage("None");
    setAccessibleOnly(false);
    setSelectedBusynessLevels([]);
    setAppliedFilters({
      languages: [],
      accessible: false,
      venueType: "",
    });
  }

  function selectCategory(venueType) {
    setAppliedFilters((current) => ({
      ...current,
      venueType:
        current.venueType === venueType ? "" : venueType,
    }));
  }

  function toggleBusynessLevel(level) {
    setSelectedBusynessLevels((current) =>
      current.includes(level)
        ? current.filter((item) => item !== level)
        : [...current, level]
    );
  }

  return (
    <main className="live-map-page">
      <div
        ref={mapContainerRef}
        className="manhattan-map-viewport"
      />

      {mapError && (
        <div className="map-api-message" role="alert">
          {mapError}
        </div>
      )}

      {isLoading && (
        <div className="map-api-message">
          {t("liveHelpMap.loadingVenues")}
        </div>
      )}

      {!showRoutePlanner ? (
        <>
          <section className="map-search-bar">
            <span>⌕</span>
            <input
              value={searchText}
              onChange={(event) =>
                setSearchText(event.target.value)
              }
              placeholder={t("liveHelpMap.searchPlaceholder")}
            />
            <button
              type="button"
              onClick={handleAdvancedFiltersClick}
            >
              ⚙ {t("liveHelpMap.advancedFilters")}
            </button>
          </section>

          <section className="map-category-pills">
            <button
              type="button"
              className={
                appliedFilters.venueType === "clinic"
                  ? "active"
                  : ""
              }
              onClick={() => selectCategory("clinic")}
            >
              ✚ {t("liveHelpMap.categories.clinics")}
            </button>
            <button
              type="button"
              className={
                appliedFilters.venueType === "hospital"
                  ? "active"
                  : ""
              }
              aria-pressed={
                appliedFilters.venueType === "hospital"
              }
              onClick={() => selectCategory("hospital")}
            >
              🏥 {t("liveHelpMap.categories.hospitals")}
            </button>
            <button
              type="button"
              className={
                appliedFilters.venueType === "pharmacy"
                  ? "active"
                  : ""
              }
              onClick={() => selectCategory("pharmacy")}
            >
              ⚕ {t("liveHelpMap.categories.pharmacy")}
            </button>
            <button
              type="button"
              className={
                appliedFilters.venueType === "emergencyasset"
                  ? "active"
                  : ""
              }
              onClick={() =>
                selectCategory("emergencyasset")
              }
            >
              ❤️ {t("liveHelpMap.categories.aed")}
            </button>
            <button
              type="button"
              className={
                appliedFilters.venueType === "restroom"
                  ? "active"
                  : ""
              }
              onClick={() => selectCategory("restroom")}
            >
              🚽 {t("liveHelpMap.categories.toilets")}
            </button>
          </section>
        </>
      ) : (
        selectedVenue && (
          <section className="route-planner-shell">
            <div className="route-planner-bar">
              <label>
                <span>⌾</span>
                <input
                  type="text"
                  value={routeStart}
                  readOnly
                  placeholder={t("liveHelpMap.userLocationMock")}
                />
              </label>

              <label>
                <span>⌖</span>
                <input
                  type="text"
                  value={routeDestination}
                  readOnly
                  placeholder={selectedVenue.name}
                />
              </label>

              <label>
                <span>◷</span>
                <input
                  type="text"
                  value={routeDepartureTime}
                  readOnly
                  placeholder={t("liveHelpMap.routePlanner.leaveNow")}
                />
              </label>

              <button
                type="button"
                className="route-search-btn"
                onClick={handleRouteSearch}
                disabled={routeLoading}
              >
                {routeLoading
                  ? t("liveHelpMap.routePlanner.searching")
                  : `⇅ ${t("liveHelpMap.routePlanner.searchRoute")}`}
              </button>
            </div>

            <aside className="direction-options-card">
              <div className="direction-options-header">
                <h3>{t("liveHelpMap.routePlanner.directionOptions")}</h3>
                <button
                  type="button"
                  onClick={closeRoutePlanner}
                >
                  ×
                </button>
              </div>

              <div className="transport-tabs">
                {Object.entries(TRAVEL_MODE_UI).map(
                  ([mode, modeUi]) => (
                    <button
                      key={mode}
                      type="button"
                      className={
                        selectedTravelMode === mode
                          ? "active"
                          : ""
                      }
                      aria-pressed={
                        selectedTravelMode === mode
                      }
                      disabled={routeLoading}
                      onClick={() =>
                        handleTravelModeChange(mode)
                      }
                    >
                      {t(modeUi.labelKey)}
                    </button>
                  )
                )}
              </div>

              <div className="route-option active">
                <div className="route-option-top">
                  <div>
                    <strong>
                      {TRAVEL_MODE_UI[selectedTravelMode].icon}{" "}
                      {t(TRAVEL_MODE_UI[selectedTravelMode].routeLabelKey)}
                    </strong>
                    <p>
                      {selectedRouteOption?.summary ??
                        `${t(TRAVEL_MODE_UI[selectedTravelMode].labelKey)} route`}
                      {" • "}
                      {formatRouteStatus(
                        selectedRouteOption?.status
                      )}
                    </p>
                  </div>

                  <strong>
                    {routeLoading
                      ? `${t("common.loading")}`
                      : Number.isFinite(
                            selectedRouteOption
                              ?.duration_minutes
                          )
                        ? `${selectedRouteOption.duration_minutes} mins`
                        : "— mins"}
                  </strong>
                </div>

                {routeError && (
                  <p className="route-error" role="alert">
                    {routeError}
                  </p>
                )}

                {!routeLoading &&
                  !routeError &&
                  routeDetail?.steps?.length > 0 && (
                    <div className="route-steps">
                      <p>
                        ↑ {t("liveHelpMap.routePlanner.startFrom", {
                          location: routeStart,
                        })}
                      </p>

                      {routeDetail.steps.map(
                        (step, index) => (
                          <p key={`${index}-${step}`}>
                            {index + 1}. {step}
                          </p>
                        )
                      )}

                      <p>
                        ↑ {t("liveHelpMap.routePlanner.arriveAt", {
                          location: selectedVenue.name,
                        })}
                      </p>
                    </div>
                  )}

                {!routeLoading &&
                  !routeError &&
                  !routeDetail?.steps?.length && (
                    <p className="route-error">
                      {t("liveHelpMap.routePlanner.routeInstructionsUnavailable")}
                    </p>
                  )}
              </div>
            </aside>
          </section>
        )
      )}

      {standaloneAlerts.map((alert) => (
        <div
          className="standalone-alert-pill"
          key={alert.report_id}
        >
          <span className="standalone-alert-icon">
            {alert.icon}
          </span>
          <span className="standalone-alert-text">
            {alert.message} | {t("liveHelpMap.usersConfirmed", {
              count: alert.confirmations,
            })}
          </span>
        </div>
      ))}

      {showLeftDrawer && selectedVenue && (
        <aside className="map-info-card">
          <button
            className="close-card"
            type="button"
            onClick={() => setShowLeftDrawer(false)}
          >
            ×
          </button>

          <h3>{selectedVenue.name}</h3>

          <p className="open-status">
            ●{" "}
            {selectedVenue.open_now === true
              ? t("liveHelpMap.openNow")
              : selectedVenue.open_now === false
                ? t("liveHelpMap.closed")
                : t("liveHelpMap.hoursUnknown")}{" "}
            • {selectedVenue.busyness_level || t("liveHelpMap.legend.noLiveInfo")}
          </p>

          {landmarkAlert && (
            <div className="landmark-alert-banner">
              <span className="landmark-alert-icon">
                {landmarkAlert.icon}
              </span>
              <span className="landmark-alert-text">
                {landmarkAlert.message} |{" "}
                {t("liveHelpMap.usersConfirmed", {
                  count: landmarkAlert.confirmations,
                })}
              </span>
            </div>
          )}

          {selectedAccessibilityReports.length > 0 && (
            <div className="alert-box">
              <strong>
                ⓘ {t("liveHelpMap.accessibilityWarning")}
              </strong>
              <p>
                {t("liveHelpMap.accessibilityReportsConfirmed", {
                  count: selectedAccessibilityReports.length,
                })}
              </p>
            </div>
          )}

          <h4>{t("liveHelpMap.locationInfoHeading")}</h4>
          <p>
            📍 {selectedVenue.borough || t("liveHelpMap.borough")}
            <br />
            {selectedVenue.address || t("liveHelpMap.addressUnavailable")}
            <br />
            {selectedVenue.avg_wait_minutes != null
              ? t("liveHelpMap.estimatedWaitMinutes", {
                  minutes: selectedVenue.avg_wait_minutes,
                })
              : t("liveHelpMap.estimatedWaitUnavailable")}
          </p>

          <p className="venue-meta-line">
            📞 {selectedVenue.phone || t("liveHelpMap.phoneUnavailable")}
          </p>
          <p className="venue-meta-line">
            🕐{" "}
            {selectedVenue.opening_hours ||
              t("liveHelpMap.openingHoursUnavailable")}
          </p>

          <p>
            {t("map.filters.language")}:{" "}
            {(selectedVenue.language_tags ?? []).length
              ? selectedVenue.language_tags.join(", ")
              : t("liveHelpMap.languagesNotListed")}
          </p>
          <p>
            {t("favourites.access")}:{" "}
            {selectedVenue.accessible_status ||
              t("liveHelpMap.accessNotSpecified")}
          </p>

          {(selectedVenue.supported_services ?? []).length >
            0 && (
            <div className="service-tags">
              {selectedVenue.supported_services.map(
                (service) => (
                  <span
                    className="service-tag"
                    key={service}
                  >
                    {service}
                  </span>
                )
              )}
            </div>
          )}

          {autoCurrentTime ? (
            <>
              <h4 className="busyness-heading">
                {t("liveHelpMap.busynessPredictionHeading")}
              </h4>

              {(selectedVenue.busyness_forecast_12h ?? [])
                .length > 0 ? (
                <div className="mini-bars">
                  {selectedVenue.busyness_forecast_12h.map(
                    (point) => (
                      <span
                        key={point.offset_hours}
                        style={{
                          height: `${Math.max(
                            Number(point.percent) || 0,
                            6
                          )}%`,
                        }}
                        title={`${point.percent}% ${point.level}`}
                      />
                    )
                  )}
                </div>
              ) : (
                <p className="forecast-unavailable">
                  {t("liveHelpMap.forecastUnavailable")}
                </p>
              )}
            </>
          ) : (
            <div className="prediction-tag">
              {t("liveHelpMap.predictedStatusAt", {
                time: selectedTime || t("liveHelpMap.predictedStatusFallback"),
              })}{" "}
              {selectedVenue.busyness_level ||
                t("liveHelpMap.statusUnavailable")}
            </div>
          )}

          <button
            className="primary-map-btn"
            type="button"
            onClick={handleOpenLiveDirections}
          >
            ◈ {t("liveHelpMap.openLiveDirections")}
          </button>

          {favouriteError && (
            <p className="favourite-error" role="alert">
              {favouriteError}
            </p>
          )}

          <button
            className="secondary-map-btn"
            type="button"
            onClick={handleSaveLocation}
            disabled={
              updatingFavouriteId === selectedVenue.venue_id
            }
            aria-pressed={favouriteVenueIds.includes(
              selectedVenue.venue_id
            )}
          >
            {updatingFavouriteId === selectedVenue.venue_id
              ? t("liveHelpMap.savingLocation")
              : favouriteVenueIds.includes(
                    selectedVenue.venue_id
                  )
                ? `♥ ${t("liveHelpMap.savedLocation")}`
                : `♡ ${t("liveHelpMap.saveLocation")}`}
          </button>
        </aside>
      )}

      <div className="map-legend">
        <span>
          <b className="quiet-dot" /> {t("liveHelpMap.legend.quiet")}
        </span>
        <span>
          <b className="moderate-dot" /> {t("liveHelpMap.legend.moderate")}
        </span>
        <span>
          <b className="busy-dot" /> {t("liveHelpMap.legend.busy")}
        </span>
        <span>
          <b className="info-dot" /> {t("liveHelpMap.legend.noLiveInfo")}
        </span>
      </div>

      {showFilters && (
        <div className="filter-overlay">
          <section className="filter-modal">
            <div className="filter-header">
              <h2>{t("liveHelpMap.filterModal.title")}</h2>
              <button
                type="button"
                onClick={() => setShowFilters(false)}
              >
                ×
              </button>
            </div>

            <div className="filter-body">
              <div className="filter-title-row">
                <h3>{t("liveHelpMap.filterModal.availabilityDateTime")}</h3>

                <label className="auto-toggle">
                  {t("liveHelpMap.filterModal.autoCurrentTime")}
                  <button
                    type="button"
                    className={
                      autoCurrentTime
                        ? "toggle active"
                        : "toggle"
                    }
                    onClick={() =>
                      setAutoCurrentTime(
                        (current) => !current
                      )
                    }
                  />
                </label>
              </div>

              {!autoCurrentTime && (
                <div className="date-time-grid">
                  <label>
                    {t("liveHelpMap.filterModal.date")}
                    <input
                      type="date"
                      value={selectedDate}
                      onChange={(event) =>
                        setSelectedDate(
                          event.target.value
                        )
                      }
                    />
                  </label>

                  <label>
                    {t("liveHelpMap.filterModal.time")}
                    <input
                      type="time"
                      value={selectedTime}
                      onChange={(event) =>
                        setSelectedTime(
                          event.target.value
                        )
                      }
                    />
                  </label>
                </div>
              )}

              <h3>{t("liveHelpMap.filterModal.language")}</h3>

              <label>
                {t("liveHelpMap.filterModal.primaryLanguage")}
                <select
                  value={primaryLanguage}
                  onChange={(event) =>
                    setPrimaryLanguage(
                      event.target.value
                    )
                  }
                >
                  <option value=""> {t("liveHelpMap.filterModal.anyLanguage")}</option>
                  {Object.keys(LANGUAGE_CODES).map(
                    (language) => (
                      <option key={language} value={language}>
                        {language}
                      </option>
                    )
                  )}
                </select>
              </label>

              <label>
                {t("liveHelpMap.filterModal.secondaryLanguage")}
                <select
                  value={secondaryLanguage}
                  onChange={(event) =>
                    setSecondaryLanguage(
                      event.target.value
                    )
                  }
                >
                  <option>{t("liveHelpMap.filterModal.none")}</option>
                  {Object.keys(LANGUAGE_CODES).map(
                    (language) => (
                      <option key={language}>
                        {language}
                      </option>
                    )
                  )}
                </select>
              </label>

              {autoCurrentTime && (
                <>
                  <h3>{t("liveHelpMap.filterModal.busynessLevel")}</h3>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={selectedBusynessLevels.includes(
                        "quiet"
                      )}
                      onChange={() =>
                        toggleBusynessLevel("quiet")
                      }
                    />
                    <span className="quiet-dot" />
                    {t("liveHelpMap.filterModal.quietOption")}
                  </label>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={selectedBusynessLevels.includes(
                        "moderate"
                      )}
                      onChange={() =>
                        toggleBusynessLevel("moderate")
                      }
                    />
                    <span className="moderate-dot" />
                    {t("liveHelpMap.filterModal.moderateOption")}
                  </label>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={selectedBusynessLevels.includes(
                        "busy"
                      )}
                      onChange={() =>
                        toggleBusynessLevel("busy")
                      }
                    />
                    <span className="busy-dot" />
                    {t("liveHelpMap.filterModal.busyOption")}
                  </label>
                </>
              )}

              <h3>{t("liveHelpMap.filterModal.accessibilityFeatures")}</h3>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={accessibleOnly}
                  onChange={(event) =>
                    setAccessibleOnly(
                      event.target.checked
                    )
                  }
                />
                {t("liveHelpMap.filterModal.fullWheelchairAccess")}
              </label>
            </div>

            <div className="filter-footer">
              <button
                type="button"
                className="clear-btn"
                onClick={clearFilters}
              >
                {t("liveHelpMap.filterModal.clearAll")}
              </button>
              <button
                type="button"
                className="apply-btn"
                onClick={applyFilters}
              >
                {t("liveHelpMap.filterModal.applyFilters")}
              </button>
            </div>
          </section>
        </div>
      )}

      <ChatbotWidget />
    </main>
  );
}

export default LiveHelpMap;

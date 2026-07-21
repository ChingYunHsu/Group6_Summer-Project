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

import {
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

function getStoredUserLocation() {
  try {
    const storedLocation = JSON.parse(
      localStorage.getItem("clearPathUserLocation") || "null"
    );

    const lat = Number(
      storedLocation?.lat ?? storedLocation?.latitude
    );

    const lng = Number(
      storedLocation?.lng ??
        storedLocation?.lon ??
        storedLocation?.longitude
    );

    if (
      Number.isFinite(lat) &&
      Number.isFinite(lng)
    ) {
      return {
        lat,
        lng,
        isMock: false,
      };
    }
  } catch (error) {
    console.error(
      "Could not read stored user location:",
      error
    );
  }

  return null;
}

function getIssueMessage(issueType) {
  const messages = {
    elevator_broken: "Elevator reported broken",
    wheelchair_lift_broken: "Wheelchair lift reported broken",
    toilet_out_of_order: "Toilet reported out of order",
    large_crowd: "Large crowd reported",
    long_waiting_time: "Long waiting time reported",
    protest_or_blockage: "Protest or blockage reported",
    entrance_closed: "Entrance reported closed",
    ramp_blocked: "Accessibility ramp reported blocked",
    closed_early: "Venue reported closed early",
  };

  return messages[issueType] || "Active community report";
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

function normaliseReport(rawReport) {
  return {
    ...rawReport,
    report_id: rawReport.report_id ?? rawReport.id,
    message:
      rawReport.message ??
      rawReport.description ??
      getIssueMessage(rawReport.issue_type),
    confirmations:
      rawReport.confirmations ??
      rawReport.confirmation_count ??
      rawReport.confirmed_count ??
      0,
    icon: rawReport.icon ?? getReportIcon(rawReport.issue_type),
  };
}

function getTransitMinutes(venue) {
  const distance = Number(venue?.distance_km ?? 0);
  return Math.ceil(distance * 6);
}

function getWalkingMinutes(venue) {
  const distance = Number(venue?.distance_km ?? 0);
  return Math.ceil(distance * 14);
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
  const [showLocationAlert, setShowLocationAlert] = useState(false);
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
  const [selectedVenueId, setSelectedVenueId] = useState(null);

  const [favouriteVenueIds, setFavouriteVenueIds] = useState([]);
  const [favouriteError, setFavouriteError] = useState("");
  const [updatingFavouriteId, setUpdatingFavouriteId] =
    useState(null);

  const futureMode = !autoCurrentTime;
  const queryTime = futureMode
    ? buildQueryTime(selectedDate, selectedTime)
    : "";

  const [userLocation, setUserLocation] = useState(() => {
  return (
    getStoredUserLocation() ?? {
      ...MOCK_USER_LOCATION,
      isMock: true,
    }
  );
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
      setMapError(error.message || "Could not load venues.");
      setVenues([]);
      setSelectedVenueId(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshReports = useCallback(async () => {
    try {
      const reports = await listReports({ status: "active" });
      setLiveReports(reports.map(normaliseReport));
    } catch (error) {
      console.error("Failed to load live reports:", error);
      setMapError((current) => current || error.message);
    }
  }, []);

  /*const refreshBusyness = useCallback(async () => {
    if (venues.length === 0) {
      setBusynessByVenueId({});
      return;
    }

    const results = await Promise.allSettled(
      venues.map(async (venue) => {
        try {
          const snapshot = await getVenueBusyness(
            venue.venue_id,
            queryTime
          );

          return [
            venue.venue_id,
            normaliseBusyness(snapshot),
          ];
        } catch (error) {
          if (error.status === 404) {
            // The current backend lists these venues successfully but its
            // dedicated busyness lookup cannot find the seed IDs. In live
            // mode, keep busyness values already returned by /venues.
            // In future mode, do not pretend current data is predicted data.
            const fallbackSnapshot = futureMode
              ? {
                  busyness_percent: null,
                  busyness_level: "No Predicted Info",
                  busyness_color: "#0057e7",
                  avg_wait_minutes: null,
                }
              : normaliseBusyness(venue);

            return [venue.venue_id, fallbackSnapshot];
          }

          throw error;
        }
      })
    ); 

    const nextBusyness = {};

    for (const result of results) {
      if (result.status === "fulfilled") {
        const [venueId, snapshot] = result.value;
        nextBusyness[venueId] = snapshot;
      } else {
        console.error(
          "A busyness request failed:",
          result.reason
        );
      }
    }

    setBusynessByVenueId(nextBusyness);
  }, [futureMode, queryTime, venues]);*/

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
            "Could not load your saved locations."
        );
      }
    }

    void loadSavedFavourites();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    refreshReports();

    const interval = window.setInterval(refreshReports, 30000);
    return () => window.clearInterval(interval);
  }, [refreshReports]);

 /// useEffect(() => {
  ///  refreshBusyness();

  ///  const interval = window.setInterval(refreshBusyness, 30000);
  ///  return () => window.clearInterval(interval);
  ///}, [refreshBusyness]);

  useEffect(() => {
  const selectedType = appliedFilters.venueType;

  if (!selectedType) return;

  const venuesNeedingBusyness = venues.filter(
    (venue) =>
      venueMatchesCategory(venue, selectedType) &&
      !busynessFetchedIds.has(venue.venue_id)
  );

  if (venuesNeedingBusyness.length === 0) return;

  let cancelled = false;

  async function loadBusynessForCategory() {
    const results = await Promise.all(
      venuesNeedingBusyness.map(async (venue) => {
        try {
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
        } catch {
          return {
            venueId: venue.venue_id,
            busyness: null,
          };
        }
      })
    );

    if (cancelled) return;

    setBusynessByVenueId((current) => {
      const next = { ...current };

      results.forEach(({ venueId, busyness }) => {
        if (busyness) {
          next[venueId] = busyness;
        }
      });

      return next;
    });
    
    // Record successful and failed requests so 404 venues
    // are not requested repeatedly.
    setBusynessFetchedIds((current) => {
      const next = new Set(current);

      results.forEach(({ venueId }) => {
        next.add(venueId);
      });

      return next;
    });
  }

  void loadBusynessForCategory();

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
    ? "Mock Current Location"
    : "Current Location";

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
}, [userLocation]);

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
        `Open ${venue.name || "venue"}`
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
  }, [futureMode, openVenueDrawer, visibleVenues]);

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

  function locationTrackingEnabled() {
    return Boolean(
      userLocation &&
      !userLocation.isMock
    );
  }

  function handleAdvancedFiltersClick() {
    if (!locationTrackingEnabled()) {
      setShowLocationAlert(true);
      return;
    }

    setShowFilters(true);
  }

  function handleAllowAccess() {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const realLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        isMock: false,
      };

      localStorage.setItem(
        "clearPathUserLocation",
        JSON.stringify({
          lat: realLocation.lat,
          lng: realLocation.lng,
        })
      );

      setUserLocation(realLocation);

      setShowLocationAlert(false);

      if (!showRoutePlanner) {
        setShowFilters(true);
      }
    },
    (error) => {
      console.warn(
        "Location unavailable. Keeping mock Manhattan position.",
        error
      );

      setUserLocation({
        ...MOCK_USER_LOCATION,
        isMock: true,
      });

      setShowLocationAlert(false);
    }
  );
}

  async function handleSaveLocation() {
    if (!selectedVenue) return;

    const venueId =
      selectedVenue.venue_id ?? selectedVenue.id;

    if (!venueId) {
      setFavouriteError(
        "This venue does not have a valid venue ID."
      );
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
          "Could not update this saved location."
      );
    } finally {
      setUpdatingFavouriteId(null);
    }
  }

  function handleOpenLiveDirections() {
    if (!selectedVenue) return;

    setShowRoutePlanner(true);
    setShowLeftDrawer(false);
    setRouteStart("Current Location");
    setRouteDestination(selectedVenue.name);
    setRouteDepartureTime("Leave Now");

    if (!locationTrackingEnabled()) {
      setShowLocationAlert(true);
    }
  }

  function closeRoutePlanner() {
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
          Loading live venue data...
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
              placeholder="Search clinics or pharmacies..."
            />
            <button
              type="button"
              onClick={handleAdvancedFiltersClick}
            >
              ⚙ Advanced Filters
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
              ✚ Clinics
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
              🏥 Hospitals
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
              ⚕ Pharmacy
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
              ❤️ AED
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
              🚽 Toilets
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
                  onChange={(event) =>
                    setRouteStart(event.target.value)
                  }
                  placeholder="Current Location"
                />
              </label>

              <label>
                <span>⌖</span>
                <input
                  type="text"
                  value={routeDestination}
                  onChange={(event) =>
                    setRouteDestination(event.target.value)
                  }
                  placeholder={selectedVenue.name}
                />
              </label>

              <label>
                <span>◷</span>
                <input
                  type="text"
                  value={routeDepartureTime}
                  onChange={(event) =>
                    setRouteDepartureTime(event.target.value)
                  }
                  placeholder="Leave Now"
                />
              </label>

              <button
                type="button"
                className="route-search-btn"
              >
                ⇅ Search Route
              </button>
            </div>

            <aside className="direction-options-card">
              <div className="direction-options-header">
                <h3>Direction Options</h3>
                <button
                  type="button"
                  onClick={closeRoutePlanner}
                >
                  ×
                </button>
              </div>

              <div className="transport-tabs">
                <button type="button">Walking</button>
                <button type="button" className="active">
                  Transit
                </button>
                <button type="button">Driving</button>
              </div>

              <div className="route-option active">
                <div className="route-option-top">
                  <div>
                    <strong>🚇 Transit Route</strong>
                    <p>
                      To {selectedVenue.name} •{" "}
                      {selectedVenue.distance_km ?? "—"} km
                    </p>
                  </div>
                  <strong>
                    {getTransitMinutes(selectedVenue)} mins
                  </strong>
                </div>

                <div className="route-steps">
                  <p>
                    ↟ Start from{" "}
                    {routeStart || "Current Location"}
                  </p>
                  <p>
                    ● Travel toward{" "}
                    {selectedVenue.borough || "the venue"}
                  </p>
                  <p>
                    ● Continue to{" "}
                    {selectedVenue.address || "the destination"}
                  </p>
                  <p>↟ Arrive at {selectedVenue.name}</p>
                </div>
              </div>

              <div className="route-option">
                <div className="route-option-top">
                  <div>
                    <strong>🚶 Walking Route</strong>
                    <p>
                      {selectedVenue.distance_km ?? "—"} km •{" "}
                      {selectedVenue.accessible_status ||
                        "Accessibility unknown"}
                    </p>
                  </div>
                  <strong>
                    {getWalkingMinutes(selectedVenue)} mins
                  </strong>
                </div>
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
            {alert.message} | {alert.confirmations} users
            confirmed
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
              ? "Open Now"
              : selectedVenue.open_now === false
                ? "Closed"
                : "Hours Unknown"}{" "}
            • {selectedVenue.busyness_level || "No Live Info"}
          </p>

          {landmarkAlert && (
            <div className="landmark-alert-banner">
              <span className="landmark-alert-icon">
                {landmarkAlert.icon}
              </span>
              <span className="landmark-alert-text">
                {landmarkAlert.message} |{" "}
                {landmarkAlert.confirmations} users confirmed
              </span>
            </div>
          )}

          {selectedAccessibilityReports.length > 0 && (
            <div className="alert-box">
              <strong>
                ⓘ Active Accessibility Warning
              </strong>
              <p>
                {selectedAccessibilityReports.length} accessibility reports
                confirmed
              </p>
            </div>
          )}

          <h4>LOCATION INFO</h4>
          <p>
            📍 {selectedVenue.borough || "Borough unknown"}
            <br />
            {selectedVenue.address || "Address unavailable"}
            <br />
            {selectedVenue.avg_wait_minutes != null
              ? `${selectedVenue.avg_wait_minutes} min estimated wait`
              : "Estimated wait unavailable"}
          </p>

          <p className="venue-meta-line">
            📞 {selectedVenue.phone || "Not available"}
          </p>
          <p className="venue-meta-line">
            🕐{" "}
            {selectedVenue.opening_hours ||
              "Opening hours unavailable"}
          </p>

          <p>
            Languages:{" "}
            {(selectedVenue.language_tags ?? []).length
              ? selectedVenue.language_tags.join(", ")
              : "Not listed"}
          </p>
          <p>
            Access:{" "}
            {selectedVenue.accessible_status ||
              "Not specified"}
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
                12-HOUR BUSYNESS PREDICTION
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
                            8
                          )}px`,
                        }}
                        title={`${point.percent}% ${point.level}`}
                      />
                    )
                  )}
                </div>
              ) : (
                <p className="forecast-unavailable">
                  Forecast data is not currently available.
                </p>
              )}
            </>
          ) : (
            <div className="prediction-tag">
              Predicted Status at{" "}
              {selectedTime || "Selected Time"}:{" "}
              {selectedVenue.busyness_level ||
                "Unavailable"}
            </div>
          )}

          <button
            className="primary-map-btn"
            type="button"
            onClick={handleOpenLiveDirections}
          >
            ◈ Open Live Directions
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
              ? "Saving..."
              : favouriteVenueIds.includes(
                    selectedVenue.venue_id
                  )
                ? "♥ Saved Location"
                : "♡ Save Location"}
          </button>
        </aside>
      )}

      <div className="map-legend">
        <span>
          <b className="quiet-dot" /> Quiet
        </span>
        <span>
          <b className="moderate-dot" /> Moderate
        </span>
        <span>
          <b className="busy-dot" /> Busy
        </span>
        <span>
          <b className="info-dot" /> No Live Info
        </span>
      </div>

      {showFilters && (
        <div className="filter-overlay">
          <section className="filter-modal">
            <div className="filter-header">
              <h2>Advanced Filters</h2>
              <button
                type="button"
                onClick={() => setShowFilters(false)}
              >
                ×
              </button>
            </div>

            <div className="filter-body">
              <div className="filter-title-row">
                <h3>AVAILABILITY DATE & TIME</h3>

                <label className="auto-toggle">
                  Auto Current Time
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
                    Date
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
                    Time
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

              <h3>LANGUAGE</h3>

              <label>
                Primary Language
                <select
                  value={primaryLanguage}
                  onChange={(event) =>
                    setPrimaryLanguage(
                      event.target.value
                    )
                  }
                >
                  <option value=""> Any language</option>
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
                Secondary Language (Optional)
                <select
                  value={secondaryLanguage}
                  onChange={(event) =>
                    setSecondaryLanguage(
                      event.target.value
                    )
                  }
                >
                  <option>None</option>
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
                  <h3>BUSYNESS LEVEL</h3>
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
                    Quiet (Under 30% load)
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
                    Moderate (30% - 70% load)
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
                    Busy (Over 70% load)
                  </label>
                </>
              )}

              <h3>ACCESSIBILITY FEATURES</h3>
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
                Full Wheelchair Access
              </label>
            </div>

            <div className="filter-footer">
              <button
                type="button"
                className="clear-btn"
                onClick={clearFilters}
              >
                Clear All
              </button>
              <button
                type="button"
                className="apply-btn"
                onClick={applyFilters}
              >
                Apply Filters
              </button>
            </div>
          </section>
        </div>
      )}

      {showLocationAlert && (
        <div className="filter-overlay">
          <section className="location-alert-modal">
            <h2>Location Access Required</h2>
            <p>
              To use accessibility tracking filters and live
              directions, please allow location access.
            </p>

            <div className="location-alert-actions">
              <button
                type="button"
                onClick={() =>
                  setShowLocationAlert(false)
                }
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAllowAccess}
              >
                Allow Access
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default LiveHelpMap;
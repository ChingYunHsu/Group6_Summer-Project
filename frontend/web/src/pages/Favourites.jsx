import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  deleteFavourite,
  listFavourites,
} from "../services/FavouritesApi";
import {
  getVenueBusyness,
  getVenueById,
} from "../services/LiveHelpMapApi";
import "./Favourites.css";

function getFavouriteVenueId(favourite) {
  return (
    favourite?.venue_id ??
    favourite?.venueId ??
    favourite?.venue?.venue_id ??
    favourite?.venue?.id ??
    null
  );
}

function unwrapVenuePayload(payload) {
  if (!payload || typeof payload !== "object") {
    return {};
  }

  const unwrapped =
    payload.venue ??
    payload.item ??
    payload.result ??
    payload.data?.venue ??
    payload.data?.item ??
    payload.data ??
    payload;

  return unwrapped &&
    typeof unwrapped === "object" &&
    !Array.isArray(unwrapped)
    ? unwrapped
    : {};
}

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

function normaliseAccessStatus(value) {
  if (typeof value === "boolean") {
    return value ? "accessible" : "not accessible";
  }

  const cleanedValue = String(value ?? "").trim();

  return cleanedValue || "";
}

function normaliseBusyness(payload) {
  const rawBusyness =
    payload?.busyness ??
    payload?.data?.busyness ??
    payload?.data ??
    payload ??
    {};

  if (
    !rawBusyness ||
    typeof rawBusyness !== "object" ||
    Array.isArray(rawBusyness)
  ) {
    return {};
  }

  const busynessPercent =
    rawBusyness.busyness_percent ??
    rawBusyness.busyness_score ??
    rawBusyness.percent ??
    rawBusyness.load_percent;

  const busynessLevel =
    rawBusyness.busyness_level ??
    rawBusyness.busyness_status ??
    rawBusyness.level ??
    rawBusyness.status;

  const numericBusynessPercent =
    busynessPercent !== null &&
    busynessPercent !== undefined &&
    busynessPercent !== ""
      ? Number(busynessPercent)
      : Number.NaN;

  return {
    ...(Number.isFinite(numericBusynessPercent)
      ? {
          busyness_percent: Math.min(
            100,
            Math.max(0, numericBusynessPercent)
          ),
        }
      : {}),

    ...(busynessLevel
      ? {
          busyness_level: busynessLevel,
          busyness_status:
            rawBusyness.busyness_status ??
            rawBusyness.status ??
            busynessLevel,
        }
      : {}),

    ...(rawBusyness.busyness_color ??
    rawBusyness.color
      ? {
          busyness_color:
            rawBusyness.busyness_color ??
            rawBusyness.color,
        }
      : {}),
  };
}

function normaliseVenue(payload) {
  const rawVenue = unwrapVenuePayload(payload);
  const location = rawVenue.location ?? {};

  const latitude = Number(
    rawVenue.latitude ??
      rawVenue.lat ??
      location.latitude ??
      location.lat
  );

  const longitude = Number(
    rawVenue.longitude ??
      rawVenue.lng ??
      rawVenue.lon ??
      location.longitude ??
      location.lng ??
      location.lon
  );

  return {
    ...rawVenue,

    venue_id:
      rawVenue.venue_id ??
      rawVenue.venueId ??
      rawVenue.id ??
      null,

    name:
      rawVenue.name ??
      rawVenue.venue_name ??
      rawVenue.title ??
      "",

    venue_type:
      rawVenue.venue_type ??
      rawVenue.type ??
      rawVenue.category ??
      "",

    borough:
      rawVenue.borough ??
      rawVenue.district ??
      rawVenue.area ??
      rawVenue.city ??
      "",

    address:
      rawVenue.address ??
      rawVenue.formatted_address ??
      rawVenue.street_address ??
      "",

    latitude: Number.isFinite(latitude) ? latitude : null,
    longitude: Number.isFinite(longitude) ? longitude : null,

    supported_services: normaliseList(
      rawVenue.supported_services ??
        rawVenue.services
    ),

    language_tags: normaliseList(
      rawVenue.language_tags ??
        rawVenue.languages
    ),

    accessible_status: normaliseAccessStatus(
      rawVenue.accessible_status ??
        rawVenue.access_status ??
        rawVenue.wheelchair_accessible ??
        rawVenue.accessible ??
        rawVenue.accessibility
    ),

    busyness_percent:
      rawVenue.busyness_percent ??
      rawVenue.busyness?.busyness_percent ??
      rawVenue.busyness?.percent ??
      null,

    busyness_level:
      rawVenue.busyness_level ??
      rawVenue.busyness?.busyness_level ??
      rawVenue.busyness?.level ??
      rawVenue.busyness?.status ??
      "No Live Info",
  };
}

function getSavedUserLocation() {
  try {
    const storedLocation = JSON.parse(
      localStorage.getItem("clearPathUserLocation") ||
        "null"
    );

    const latitude = Number(
      storedLocation?.latitude ??
        storedLocation?.lat
    );

    const longitude = Number(
      storedLocation?.longitude ??
        storedLocation?.lng ??
        storedLocation?.lon
    );

    if (
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
    ) {
      return { latitude, longitude };
    }
  } catch (error) {
    console.error(
      "Could not read the saved user location:",
      error
    );
  }

  return null;
}

function calculateDistanceKm(
  originLatitude,
  originLongitude,
  destinationLatitude,
  destinationLongitude
) {
  const earthRadiusKm = 6371;
  const toRadians = (degrees) =>
    (degrees * Math.PI) / 180;

  const latitudeDifference = toRadians(
    destinationLatitude - originLatitude
  );

  const longitudeDifference = toRadians(
    destinationLongitude - originLongitude
  );

  const firstLatitude = toRadians(originLatitude);
  const secondLatitude = toRadians(destinationLatitude);

  const haversineValue =
    Math.sin(latitudeDifference / 2) ** 2 +
    Math.cos(firstLatitude) *
      Math.cos(secondLatitude) *
      Math.sin(longitudeDifference / 2) ** 2;

  const angularDistance =
    2 *
    Math.atan2(
      Math.sqrt(haversineValue),
      Math.sqrt(1 - haversineValue)
    );

  return Number(
    (earthRadiusKm * angularDistance).toFixed(1)
  );
}

function addDistanceFromSavedLocation(
  venue,
  savedUserLocation
) {
  const hasApiDistance =
    venue.distance_km !== null &&
    venue.distance_km !== undefined &&
    venue.distance_km !== "";

  const apiDistance = hasApiDistance
    ? Number(venue.distance_km)
    : Number.NaN;

  if (Number.isFinite(apiDistance)) {
    return {
      ...venue,
      distance_km: apiDistance,
    };
  }

  if (
    !savedUserLocation ||
    !Number.isFinite(venue.latitude) ||
    !Number.isFinite(venue.longitude)
  ) {
    return {
      ...venue,
      distance_km: null,
    };
  }

  return {
    ...venue,
    distance_km: calculateDistanceKm(
      savedUserLocation.latitude,
      savedUserLocation.longitude,
      venue.latitude,
      venue.longitude
    ),
  };
}

function getOperationalStatus(venue) {
  if (
    venue.active_warning ||
    venue.live_status_badge === "DIVERTING"
  ) {
    return "DIVERTING";
  }

  if (venue.busyness_percent >= 80) {
    return "HIGH CAPACITY";
  }

  if (venue.busyness_percent >= 40) {
    return "MODERATE";
  }

  if (venue.busyness_percent == null) {
    return "NO LIVE INFO";
  }

  return "OPTIMAL FLOW";
}

function getStatusClass(status) {
  return status.toLowerCase().replaceAll(" ", "-");
}

function getStatusLabel(status, t) {
  const map = {
    DIVERTING: t("favourites.status.diverting"),
    "HIGH CAPACITY": t("favourites.status.highCapacity"),
    MODERATE: t("favourites.status.moderate"),
    "NO LIVE INFO": t("favourites.status.noLiveInfo"),
    "OPTIMAL FLOW": t("favourites.status.optimalFlow"),
  };

  return map[status] ?? status;
}

function Favourites() {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  const [savedVenues, setSavedVenues] = useState([]);
  const [activeFilter, setActiveFilter] =
    useState("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [removingVenueId, setRemovingVenueId] =
    useState(null);
  const [error, setError] = useState("");

  const loadFavourites = useCallback(
    async ({ silent = false } = {}) => {
      try {
        /*
         * Do not synchronously call a state setter here.
         * This function is called directly by useEffect.
         */
        const favouriteRecords =
          await listFavourites();

        const savedUserLocation =
          getSavedUserLocation();

        const venueResults = await Promise.allSettled(
          favouriteRecords.map(async (favourite) => {
            const venueId =
              getFavouriteVenueId(favourite);

            if (!venueId) {
              throw new Error(
                t("favourites.notProvidedVenueId")
              );
            }

            const embeddedVenue =
              favourite.venue &&
              typeof favourite.venue === "object"
                ? unwrapVenuePayload(favourite.venue)
                : unwrapVenuePayload(favourite);

            const [
              detailsResult,
              busynessResult,
            ] = await Promise.allSettled([
              getVenueById(venueId),
              getVenueBusyness(venueId),
            ]);

            const apiVenue =
              detailsResult.status === "fulfilled"
                ? unwrapVenuePayload(
                    detailsResult.value
                  )
                : {};

            const apiBusyness =
              busynessResult.status === "fulfilled"
                ? normaliseBusyness(
                    busynessResult.value
                  )
                : {};

            if (
              detailsResult.status === "rejected"
            ) {
              console.error(
                `Failed to load details for venue ${venueId}:`,
                detailsResult.reason
              );
            }

            if (
              busynessResult.status === "rejected"
            ) {
              console.error(
                `Failed to load busyness for venue ${venueId}:`,
                busynessResult.reason
              );
            }

            const hydratedVenue = normaliseVenue({
              ...embeddedVenue,
              ...apiVenue,
              ...apiBusyness,
              venue_id: venueId,
            });

            return addDistanceFromSavedLocation(
              hydratedVenue,
              savedUserLocation
            );
          })
        );

        const loadedVenues = venueResults
          .filter(
            (result) =>
              result.status === "fulfilled"
          )
          .map((result) => result.value)
          .filter((venue) => venue?.venue_id);

        const failedCount =
          venueResults.length - loadedVenues.length;

        if (failedCount > 0) {
          setError(
            t(
              failedCount === 1
                ? "favourites.failedToLoadSingular"
                : "favourites.failedToLoadPlural",
              { count: failedCount }
            )
          );
        } else {
          setError("");
        }

        setSavedVenues(loadedVenues);
      } catch (loadError) {
        console.error(
          "Failed to load favourites:",
          loadError
        );

        setError(
          loadError.message ||
            t("favourites.couldNotLoad")
        );

        setSavedVenues([]);
      } finally {
        if (!silent) {
          setIsLoading(false);
        }
      }
    },
    [t]
  );

  useEffect(() => {
    const initialLoadTimeout = window.setTimeout(() => {
      void loadFavourites();
    }, 0);

    const telemetryRefresh = window.setInterval(() => {
      void loadFavourites({ silent: true });
    }, 30000);

    return () => {
      window.clearTimeout(initialLoadTimeout);
      window.clearInterval(telemetryRefresh);
    };
  }, [loadFavourites]);

  const filteredVenues = useMemo(() => {
    if (activeFilter === "ALL") {
      return savedVenues;
    }

    return savedVenues.filter(
      (venue) =>
        getOperationalStatus(venue) === activeFilter
    );
  }, [savedVenues, activeFilter]);

  function handleRetry() {
    setIsLoading(true);
    setError("");
    void loadFavourites();
  }

  async function removeSavedVenue(venueId) {
    try {
      setRemovingVenueId(venueId);
      setError("");

      await deleteFavourite(venueId);

      setSavedVenues((currentVenues) =>
        currentVenues.filter(
          (venue) => venue.venue_id !== venueId
        )
      );
    } catch (removeError) {
      console.error(
        "Failed to remove favourite:",
        removeError
      );

      setError(
        removeError.message ||
          t("favourites.couldNotRemove")
      );
    } finally {
      setRemovingVenueId(null);
    }
  }

  function handleGetDirections(venue) {
    localStorage.setItem(
      "clearPathDirectionsDestination",
      String(venue.venue_id)
    );

    const hasCoordinates =
      Number.isFinite(venue.latitude) &&
      Number.isFinite(venue.longitude);

    navigate("/map", {
      state: {
        venueId: venue.venue_id,
        selectedVenueId: venue.venue_id,
        destination: venue.name,
        destinationCoordinates: hasCoordinates
          ? {
              latitude: venue.latitude,
              longitude: venue.longitude,
            }
          : null,
        openRoutePlanner: true,
      },
    });
  }

  return (
    <main className="saved-locations-page">
      <section className="saved-locations-header">
        <div>
          <h1>{t("favourites.title")}</h1>

          <p>
            {t("favourites.description")}
          </p>
        </div>

        <div className="saved-header-actions">
          <button
            type="button"
            className="saved-filter-btn"
            onClick={() =>
              setActiveFilter((currentFilter) =>
                currentFilter === "ALL"
                  ? "HIGH CAPACITY"
                  : "ALL"
              )
            }
          >
            ⌕ {t("favourites.filter")}
          </button>
        </div>
      </section>

      {error && (
        <section
          className="saved-api-message"
          role="alert"
        >
          <p>{error}</p>

          <button
            type="button"
            onClick={handleRetry}
          >
            {t("favourites.tryAgain")}
          </button>
        </section>
      )}

      {activeFilter !== "ALL" && (
        <section className="saved-filter-tabs">
          <button
            type="button"
            className={
              activeFilter === "ALL" ? "active" : ""
            }
            onClick={() => setActiveFilter("ALL")}
          >
            {t("favourites.filters.all")}
          </button>

          <button
            type="button"
            className={
              activeFilter === "HIGH CAPACITY"
                ? "active"
                : ""
            }
            onClick={() =>
              setActiveFilter("HIGH CAPACITY")
            }
          >
            {t("favourites.filters.highCapacity")}
          </button>

          <button
            type="button"
            className={
              activeFilter === "MODERATE"
                ? "active"
                : ""
            }
            onClick={() =>
              setActiveFilter("MODERATE")
            }
          >
            {t("favourites.filters.moderate")}
          </button>

          <button
            type="button"
            className={
              activeFilter === "OPTIMAL FLOW"
                ? "active"
                : ""
            }
            onClick={() =>
              setActiveFilter("OPTIMAL FLOW")
            }
          >
            {t("favourites.filters.optimalFlow")}
          </button>

          <button
            type="button"
            className={
              activeFilter === "DIVERTING"
                ? "active"
                : ""
            }
            onClick={() =>
              setActiveFilter("DIVERTING")
            }
          >
            {t("favourites.filters.diverting")}
          </button>

          <button
            type="button"
            className={
              activeFilter === "NO LIVE INFO"
                ? "active"
                : ""
            }
            onClick={() =>
              setActiveFilter("NO LIVE INFO")
            }
          >
            {t("favourites.filters.noLiveInfo")}
          </button>
        </section>
      )}

      {isLoading ? (
        <section className="saved-empty-state">
          <h2>{t("favourites.loadingTitle")}</h2>

          <p>
            {t("favourites.loadingBody")}
          </p>
        </section>
      ) : savedVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>{t("favourites.emptyTitle")}</h2>

          <p>
            {t("favourites.emptyBody")}
          </p>
        </section>
      ) : filteredVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>{t("favourites.noMatchTitle")}</h2>

          <p>
            {t("favourites.noMatchBody")}
          </p>
        </section>
      ) : (
        <section className="saved-card-grid">
          {filteredVenues.map((venue) => {
            const status =
              getOperationalStatus(venue);

            const statusClass =
              getStatusClass(status);

            const isRemoving =
              removingVenueId === venue.venue_id;

            return (
              <article
                className={`saved-location-card ${statusClass}`}
                key={venue.venue_id}
              >
                <div className="saved-card-top">
                  <span
                    className={`status-tag ${statusClass}`}
                  >
                    ● {getStatusLabel(status, t)}
                  </span>

                  <button
                    type="button"
                    className="saved-heart-btn"
                    onClick={() =>
                      removeSavedVenue(
                        venue.venue_id
                      )
                    }
                    disabled={isRemoving}
                    aria-label={t("favourites.removeVenue", {
                      name: venue.name || t("favourites.unnamedVenue"),
                    })}
                  >
                    {isRemoving ? t("favourites.removingEllipsis") : "♥"}
                  </button>
                </div>

                <h2>
                  {venue.name || t("favourites.unnamedVenue")}
                </h2>

                <p className="saved-distance-line">
                  ⊙{" "}
                  {venue.distance_km != null
                    ? t("favourites.distanceAway", {
                        distance: venue.distance_km,
                      })
                    : t("favourites.distanceUnavailable")}{" "}
                  •{" "}
                  {venue.borough ||
                    venue.address ||
                    t("favourites.areaUnknown")}
                </p>

                <p className="saved-service-line">
                  ✚{" "}
                  {venue.supported_services?.[0] ||
                    venue.venue_type ||
                    t("favourites.healthcareService")}
                </p>

                <p className="saved-meta-line">
                  {t("favourites.access")}:{" "}
                  {venue.accessible_status ||
                    t("favourites.accessNotSpecified")}
                </p>

                <button
                  type="button"
                  className="saved-directions-btn"
                  onClick={() =>
                    handleGetDirections(venue)
                  }
                >
                  ◈ {t("favourites.getDirections")}
                </button>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}

export default Favourites;
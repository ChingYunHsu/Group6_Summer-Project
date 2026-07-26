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

function normaliseVenue(rawVenue) {
  return {
    ...rawVenue,
    venue_id: rawVenue?.venue_id ?? rawVenue?.id,
    supported_services:
      rawVenue?.supported_services ??
      rawVenue?.services ??
      [],
    language_tags:
      rawVenue?.language_tags ??
      rawVenue?.languages ??
      [],
  };
}

function normaliseBusyness(rawBusyness) {
  return {
    ...rawBusyness,
    busyness_percent:
      rawBusyness?.busyness_percent ??
      rawBusyness?.percent ??
      rawBusyness?.load_percent ??
      null,
    busyness_level:
      rawBusyness?.busyness_level ??
      rawBusyness?.level ??
      rawBusyness?.status ??
      "No Live Info",
    avg_wait_minutes:
      rawBusyness?.avg_wait_minutes ??
      rawBusyness?.estimated_wait_minutes ??
      null,
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
                ? favourite.venue
                : favourite;

            const [
              detailsResult,
              busynessResult,
            ] = await Promise.allSettled([
              getVenueById(venueId),
              getVenueBusyness(venueId),
            ]);

            const details =
              detailsResult.status === "fulfilled"
                ? detailsResult.value
                : {};

            const busyness =
              busynessResult.status === "fulfilled"
                ? busynessResult.value
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

            return {
              ...normaliseVenue(embeddedVenue),
              ...normaliseVenue(details),
              ...normaliseBusyness(busyness),
              venue_id: venueId,
            };
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
      venue.venue_id
    );

    navigate("/map");
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
                  • {venue.borough || t("favourites.areaUnknown")}
                </p>

                <p className="saved-service-line">
                  ✚{" "}
                  {venue.supported_services?.[0] ||
                    venue.venue_type ||
                    t("favourites.healthcareService")}
                </p>

                <p className="saved-meta-line">
                  {t("favourites.waitTime")}:{" "}
                  {venue.avg_wait_minutes != null
                    ? t("favourites.waitMinutes", {
                        minutes: venue.avg_wait_minutes,
                      })
                    : t("favourites.waitUnavailable")}
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

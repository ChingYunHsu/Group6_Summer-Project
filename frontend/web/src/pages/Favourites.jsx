import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
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

function Favourites() {
  const navigate = useNavigate();

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
                "A favourite record did not include venue_id."
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
            `${failedCount} saved location${
              failedCount === 1 ? "" : "s"
            } could not be loaded.`
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
            "Could not load saved locations."
        );

        setSavedVenues([]);
      } finally {
        if (!silent) {
          setIsLoading(false);
        }
      }
    },
    []
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
          "Could not remove the saved location."
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
          <h1>Saved Locations</h1>

          <p>
            Manage and monitor your primary healthcare
            response sites. View real-time capacity and
            routing information for your prioritized
            facilities.
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
            ⌕ Filter
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
            Try Again
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
            All
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
            High Capacity
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
            Moderate
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
            Optimal Flow
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
            Diverting
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
            No Live Info
          </button>
        </section>
      )}

      {isLoading ? (
        <section className="saved-empty-state">
          <h2>Loading saved locations...</h2>

          <p>
            Retrieving your favourites and current venue
            information.
          </p>
        </section>
      ) : savedVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>No saved locations yet</h2>

          <p>
            Saved healthcare facilities will appear here
            when they have been added to your account.
          </p>
        </section>
      ) : filteredVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>No locations match this filter</h2>

          <p>
            Try changing the filter to view your saved
            facilities.
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
                    ● {status}
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
                    aria-label={`Remove ${
                      venue.name || "venue"
                    }`}
                  >
                    {isRemoving ? "…" : "♥"}
                  </button>
                </div>

                <h2>
                  {venue.name || "Unnamed venue"}
                </h2>

                <p className="saved-distance-line">
                  ⊙{" "}
                  {venue.distance_km != null
                    ? `${venue.distance_km} km away`
                    : "Distance unavailable"}{" "}
                  • {venue.borough || "Area unknown"}
                </p>

                <p className="saved-service-line">
                  ✚{" "}
                  {venue.supported_services?.[0] ||
                    venue.venue_type ||
                    "Healthcare service"}
                </p>

                <p className="saved-meta-line">
                  Wait time:{" "}
                  {venue.avg_wait_minutes != null
                    ? `${venue.avg_wait_minutes} mins`
                    : "Unavailable"}
                </p>

                <p className="saved-meta-line">
                  Access:{" "}
                  {venue.accessible_status ||
                    "Not specified"}
                </p>

                <button
                  type="button"
                  className="saved-directions-btn"
                  onClick={() =>
                    handleGetDirections(venue)
                  }
                >
                  ◈ Get Directions
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
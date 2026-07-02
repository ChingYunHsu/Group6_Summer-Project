import { useEffect, useMemo, useState } from "react";
import { VENUES } from "../data/venues";
import "./Favourites.css";

const SAVED_LOCATION_KEY = "clearPathSavedVenueIds";

function getSavedVenueIds() {
  return JSON.parse(localStorage.getItem(SAVED_LOCATION_KEY) || "[]");
}

function getOperationalStatus(venue) {
  if (venue.active_warning || venue.live_status_badge === "DIVERTING") {
    return "DIVERTING";
  }

  if (venue.busyness_percent >= 80) {
    return "HIGH CAPACITY";
  }

  if (venue.busyness_percent >= 40) {
    return "MODERATE";
  }

  return "OPTIMAL FLOW";
}

function getStatusClass(status) {
  return status.toLowerCase().replaceAll(" ", "-");
}

function Favourites() {
  const [savedVenueIds, setSavedVenueIds] = useState(getSavedVenueIds);
  const [activeFilter, setActiveFilter] = useState("ALL");

  useEffect(() => {
    function syncSavedLocations() {
      setSavedVenueIds(getSavedVenueIds());
    }

    window.addEventListener("storage", syncSavedLocations);
    window.addEventListener("clearpath:saved-locations-updated", syncSavedLocations);

    const telemetryRefresh = setInterval(() => {
      setSavedVenueIds(getSavedVenueIds());
    }, 30000);

    return () => {
      window.removeEventListener("storage", syncSavedLocations);
      window.removeEventListener(
        "clearpath:saved-locations-updated",
        syncSavedLocations
      );
      clearInterval(telemetryRefresh);
    };
  }, []);

  const savedVenues = useMemo(() => {
    return savedVenueIds
      .map((venueId) => VENUES.find((venue) => venue.venue_id === venueId))
      .filter(Boolean);
  }, [savedVenueIds]);

  const filteredVenues = useMemo(() => {
    if (activeFilter === "ALL") return savedVenues;

    return savedVenues.filter((venue) => {
      return getOperationalStatus(venue) === activeFilter;
    });
  }, [savedVenues, activeFilter]);

  function removeSavedVenue(venueId) {
    const updatedSavedIds = savedVenueIds.filter((id) => id !== venueId);

    localStorage.setItem(SAVED_LOCATION_KEY, JSON.stringify(updatedSavedIds));
    setSavedVenueIds(updatedSavedIds);

    window.dispatchEvent(new Event("clearpath:saved-locations-updated"));
  }

  function handleGetDirections(venue) {
    localStorage.setItem("clearPathDirectionsDestination", venue.venue_id);
    window.location.href = "/map";
  }

  return (
    <main className="saved-locations-page">
      <section className="saved-locations-header">
        <div>
          <h1>Saved Locations</h1>
          <p>
            Manage and monitor your primary healthcare response sites. View
            real-time capacity and routing information for your prioritized
            facilities.
          </p>
        </div>

        <div className="saved-header-actions">
          <button
            type="button"
            className="saved-filter-btn"
            onClick={() =>
              setActiveFilter(activeFilter === "ALL" ? "HIGH CAPACITY" : "ALL")
            }
          >
            ⌕ Filter
          </button>
        </div>
      </section>

      {activeFilter !== "ALL" && (
        <section className="saved-filter-tabs">
          <button
            type="button"
            className={activeFilter === "ALL" ? "active" : ""}
            onClick={() => setActiveFilter("ALL")}
          >
            All
          </button>
          <button
            type="button"
            className={activeFilter === "HIGH CAPACITY" ? "active" : ""}
            onClick={() => setActiveFilter("HIGH CAPACITY")}
          >
            High Capacity
          </button>
          <button
            type="button"
            className={activeFilter === "MODERATE" ? "active" : ""}
            onClick={() => setActiveFilter("MODERATE")}
          >
            Moderate
          </button>
          <button
            type="button"
            className={activeFilter === "OPTIMAL FLOW" ? "active" : ""}
            onClick={() => setActiveFilter("OPTIMAL FLOW")}
          >
            Optimal Flow
          </button>
          <button
            type="button"
            className={activeFilter === "DIVERTING" ? "active" : ""}
            onClick={() => setActiveFilter("DIVERTING")}
          >
            Diverting
          </button>
        </section>
      )}

      {savedVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>No saved locations yet</h2>
          <p>
            Saved healthcare facilities will appear here after you add them from
            the Live Help Map.
          </p>
        </section>
      ) : filteredVenues.length === 0 ? (
        <section className="saved-empty-state">
          <h2>No locations match this filter</h2>
          <p>Try changing the filter to view your saved facilities.</p>
        </section>
      ) : (
        <section className="saved-card-grid">
          {filteredVenues.map((venue) => {
            const status = getOperationalStatus(venue);
            const statusClass = getStatusClass(status);

            return (
              <article
                className={`saved-location-card ${statusClass}`}
                key={venue.venue_id}
              >
                <div className="saved-card-top">
                  <span className={`status-tag ${statusClass}`}>
                    ● {status}
                  </span>

                  <button
                    type="button"
                    className="saved-heart-btn"
                    onClick={() => removeSavedVenue(venue.venue_id)}
                    aria-label={`Remove ${venue.name}`}
                  >
                    ♥
                  </button>
                </div>

                <h2>{venue.name}</h2>

                <p className="saved-distance-line">
                  ⊙ {venue.distance_km} km away • {venue.borough}
                </p>

                <p className="saved-service-line">
                  ✚ {venue.supported_services?.[0] || venue.venue_type}
                </p>

                <p className="saved-meta-line">
                  Wait time: {venue.avg_wait_minutes} mins
                </p>

                <p className="saved-meta-line">
                  Access: {venue.accessible_status}
                </p>

                <button
                  type="button"
                  className="saved-directions-btn"
                  onClick={() => handleGetDirections(venue)}
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
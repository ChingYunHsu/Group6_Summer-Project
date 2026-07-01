import { useEffect, useRef, useState, useCallback } from "react";
import "./LiveHelpMap.css";
import maplibregl from "maplibre-gl";
import { VENUES } from "../data/venues";
import { REPORTS, getLandmarkAlertForVenue, getStandaloneAlerts } from "../data/reports";
import "maplibre-gl/dist/maplibre-gl.css";

function getMarkerColor(venue, futureMode) {
  if (futureMode) return "#0057e7";
  if (venue.busyness_percent == null) return "#0057e7";
  if (venue.busyness_percent < 30) return "#22c55e";
  if (venue.busyness_percent <= 70) return "#eab308";
  return "#ef4444";
}

function getIcon(type) {
  if (type === "clinic") return "✚";
  if (type === "pharmacy") return "⚕";
  if (type === "aed") return "AED";
  if (type === "toilet") return "♿";
  if (type === "emergencyasset") return "AED";
  return "●";
}

function getTransitMinutes(venue) {
  return Math.ceil(venue.distance_km * 6);
}

function getWalkingMinutes(venue) {
  return Math.ceil(venue.distance_km * 14);
}

function LiveHelpMap() {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);

  const [showFilters, setShowFilters] = useState(false);
  const [showLocationAlert, setShowLocationAlert] = useState(false);
  const [showLeftDrawer, setShowLeftDrawer] = useState(true);
  const [autoCurrentTime, setAutoCurrentTime] = useState(true);
  const [selectedTime, setSelectedTime] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [liveReports, setLiveReports] = useState(REPORTS);

  const [showRoutePlanner, setShowRoutePlanner] = useState(false);
  const [routeStart, setRouteStart] = useState("");
  const [routeDestination, setRouteDestination] = useState("");
  const [routeDepartureTime, setRouteDepartureTime] = useState("");

  const [selectedVenueId, setSelectedVenueId] = useState(VENUES[0]?.venue_id);
  const openVenueDrawer = useCallback((venue) => {
  setSelectedVenueId(venue.venue_id);
  setRouteDestination(venue.name);
  setShowRoutePlanner(false);
  setShowLeftDrawer(true);
  }, []); 

  const futureMode = !autoCurrentTime;

  const selectedVenue =
    VENUES.find((venue) => venue.venue_id === selectedVenueId) || VENUES[0];

  const landmarkAlert = getLandmarkAlertForVenue(selectedVenue.venue_id);
  const standaloneAlerts = getStandaloneAlerts(liveReports);

  useEffect(() => {
    const interval = setInterval(() => {
      setLiveReports([...REPORTS]);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (mapRef.current) return;

    mapRef.current = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-73.9857, 40.758],
      zoom: 12,
    });

    mapRef.current.addControl(new maplibregl.NavigationControl(), "bottom-right");

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    VENUES.forEach((venue) => {
      const markerEl = document.createElement("button");
      markerEl.type = "button";
      markerEl.className = "venue-pin";
      markerEl.style.backgroundColor = getMarkerColor(venue, futureMode);
      markerEl.innerHTML = `<span>${getIcon(venue.venue_type)}</span>`;
      markerEl.style.pointerEvents = 'auto';
      markerEl.style.zIndex = "10";
      markerEl.style.position = "relative";

       markerEl.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        console.log("marker mousedown:", venue.name);
        openVenueDrawer(venue);
      });

      const marker = new maplibregl.Marker({ element: markerEl })
        .setLngLat([venue.longitude, venue.latitude])
        .addTo(mapRef.current);

      markersRef.current.push(marker);
    });
  }, [futureMode, openVenueDrawer]);


  function locationTrackingEnabled() {
    return !!localStorage.getItem("clearPathUserLocation");
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
        localStorage.setItem(
          "clearPathUserLocation",
          JSON.stringify({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          })
        );

        setShowLocationAlert(false);

        if (!showRoutePlanner) {
          setShowFilters(true);
        }
      },
      () => {
        setShowLocationAlert(false);
      }
    );
  }

function handleOpenLiveDirections() {
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

  


  return (
    <main className="live-map-page">
      <div ref={mapContainerRef} className="manhattan-map-viewport" />

      {!showRoutePlanner ? (
        <>
          <section className="map-search-bar">
            <span>⌕</span>
            <input placeholder="Search clinics or pharmacies..." />
            <button type="button" onClick={handleAdvancedFiltersClick}>
              ⚙ Advanced Filters
            </button>
          </section>

          <section className="map-category-pills">
            <button type="button">✚ Clinics</button>
            <button type="button">⚕ Pharmacy</button>
            <button type="button">AED</button>
            <button type="button">♿ Toilets</button>
          </section>
        </>
      ) : (
        <section className="route-planner-shell">
          <div className="route-planner-bar">
            <label>
              <span>⌾</span>
              <input
                type="text"
                value={routeStart}
                onChange={(e) => setRouteStart(e.target.value)}
                placeholder="Current Location"
              />
            </label>

            <label>
              <span>⌖</span>
              <input
                type="text"
                value={routeDestination}
                onChange={(e) => setRouteDestination(e.target.value)}
                placeholder={selectedVenue.name}
              />
            </label>

            <label>
              <span>◷</span>
              <input
                type="text"
                value={routeDepartureTime}
                onChange={(e) => setRouteDepartureTime(e.target.value)}
                placeholder="Leave Now"
              />
            </label>

            <button type="button" className="route-search-btn">
              ⇅ Search Route
            </button>
          </div>

          <aside className="direction-options-card">
            <div className="direction-options-header">
              <h3>Direction Options</h3>
              <button type="button" onClick={closeRoutePlanner}>
                ×
              </button>
            </div>

            <div className="transport-tabs">
              <button type="button">Walking</button>
              <button type="button" className="active">Transit</button>
              <button type="button">Driving</button>
            </div>

            <div className="route-option active">
              <div className="route-option-top">
                <div>
                  <strong>🚇 Transit Route</strong>
                  <p>
                    To {selectedVenue.name} • {selectedVenue.distance_km} km
                  </p>
                </div>
                <strong>{getTransitMinutes(selectedVenue)} mins</strong>
              </div>

              <div className="route-steps">
                <p>↟ Start from {routeStart || "Current Location"}</p>
                <p>● Travel toward {selectedVenue.borough}</p>
                <p>● Continue to {selectedVenue.address}</p>
                <p>↟ Arrive at {selectedVenue.name}</p>
              </div>
            </div>

            <div className="route-option">
              <div className="route-option-top">
                <div>
                  <strong>🚶 Walking Route</strong>
                  <p>
                    {selectedVenue.distance_km} km • {selectedVenue.accessible_status}
                  </p>
                </div>
                <strong>{getWalkingMinutes(selectedVenue)} mins</strong>
              </div>
            </div>
          </aside>
        </section>
      )}

      {standaloneAlerts.map((alert) => (
        <div className="standalone-alert-pill" key={alert.report_id}>
          <span className="standalone-alert-icon">{alert.icon}</span>
          <span className="standalone-alert-text">
            {alert.message} | {alert.confirmations} users confirmed
          </span>
        </div>
      ))}
    {showLeftDrawer && (
      <aside className="map-info-card">
        <button className="close-card"
         type="button"
         onClick={() => setShowLeftDrawer(false)}
         >
          ×
        </button>

        <h3>{selectedVenue.name}</h3>

        <p className="open-status">
          ● {selectedVenue.open_now ? "Open Now" : "Closed"} •{" "}
          {selectedVenue.busyness_level}
        </p>

        {landmarkAlert && (
          <div className="landmark-alert-banner">
            <span className="landmark-alert-icon">{landmarkAlert.icon}</span>
            <span className="landmark-alert-text">
              {landmarkAlert.message} | {landmarkAlert.confirmations} users confirmed
            </span>
          </div>
        )}

        {selectedVenue.active_warning && (
          <div className="alert-box">
            <strong>ⓘ Active Accessibility Warning</strong>
            <p>{selectedVenue.live_report_count} live reports confirmed</p>
          </div>
        )}

        <h4>LOCATION INFO</h4>
        <p>
          📍 {selectedVenue.borough}
          <br />
          {selectedVenue.address}
          <br />
          {selectedVenue.avg_wait_minutes} min estimated wait
        </p>

        <p className="venue-meta-line">📞 {selectedVenue.phone}</p>
        <p className="venue-meta-line">🕐 {selectedVenue.opening_hours}</p>

        <p>Languages: {selectedVenue.language_tags.join(", ")}</p>
        <p>Access: {selectedVenue.accessible_status}</p>

        {selectedVenue.supported_services?.length > 0 && (
          <div className="service-tags">
            {selectedVenue.supported_services.map((service) => (
              <span className="service-tag" key={service}>
                {service}
              </span>
            ))}
          </div>
        )}

        {autoCurrentTime ? (
          <>
            <h4 className="busyness-heading">12-HOUR BUSYNESS PREDICTION</h4>

            <div className="mini-bars">
              {selectedVenue.busyness_forecast_12h.map((point) => (
                <span
                  key={point.offset_hours}
                  style={{ height: `${Math.max(point.percent, 8)}px` }}
                  title={`${point.percent}% ${point.level}`}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="prediction-tag">
            Predicted Status at {selectedTime || "Selected Time"}:{" "}
            {selectedVenue.busyness_level}
          </div>
        )}

        <button
          className="primary-map-btn"
          type="button"
          onClick={handleOpenLiveDirections}
        >
          ◈ Open Live Directions
        </button>

        <button className="secondary-map-btn" type="button">
          ▱ Save Location
        </button>
      </aside>
      )}
      <div className="map-legend">
        <span><b className="quiet-dot" /> Quiet</span>
        <span><b className="moderate-dot" /> Moderate</span>
        <span><b className="busy-dot" /> Busy</span>
        <span><b className="info-dot" /> No Live Info</span>
      </div>

      {showFilters && (
        <div className="filter-overlay">
          <section className="filter-modal">
            <div className="filter-header">
              <h2>Advanced Filters</h2>
              <button type="button" onClick={() => setShowFilters(false)}>×</button>
            </div>

            <div className="filter-body">
              <div className="filter-title-row">
                <h3>AVAILABILITY DATE & TIME</h3>

                <label className="auto-toggle">
                  Auto Current Time
                  <button
                    type="button"
                    className={autoCurrentTime ? "toggle active" : "toggle"}
                    onClick={() => setAutoCurrentTime(!autoCurrentTime)}
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
                      onChange={(e) => setSelectedDate(e.target.value)}
                    />
                  </label>

                  <label>
                    Time
                    <input
                      type="time"
                      value={selectedTime}
                      onChange={(e) => setSelectedTime(e.target.value)}
                    />
                  </label>
                </div>
              )}

              <h3>LANGUAGE</h3>

              <label>
                Primary Language
                <select defaultValue="English (English)">
                  <option>English (English)</option>
                  <option>Français (French)</option>
                  <option>Español (Spanish)</option>
                  <option>中文 (Chinese)</option>
                  <option>العربية (Arabic)</option>
                </select>
              </label>

              <label>
                Secondary Language (Optional)
                <select defaultValue="None">
                  <option>None</option>
                  <option>English (English)</option>
                  <option>Français (French)</option>
                  <option>Español (Spanish)</option>
                  <option>中文 (Chinese)</option>
                  <option>العربية (Arabic)</option>
                </select>
              </label>

              {autoCurrentTime && (
                <>
                  <h3>BUSYNESS LEVEL</h3>
                  <label className="check-row">
                    <input type="checkbox" />
                    <span className="quiet-dot" />
                    Quiet (Under 30% load)
                  </label>
                  <label className="check-row">
                    <input type="checkbox" />
                    <span className="moderate-dot" />
                    Moderate (30% - 70% load)
                  </label>
                  <label className="check-row">
                    <input type="checkbox" />
                    <span className="busy-dot" />
                    Busy (Over 70% load)
                  </label>
                </>
              )}

              <h3>ACCESSIBILITY FEATURES</h3>
              <label className="check-row">
                <input type="checkbox" />
                Full Wheelchair Access
              </label>
            </div>

            <div className="filter-footer">
              <button type="button" className="clear-btn">Clear All</button>
              <button
                type="button"
                className="apply-btn"
                onClick={() => setShowFilters(false)}
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
              To use accessibility tracking filters and live directions,
              please allow location access.
            </p>

            <div className="location-alert-actions">
              <button type="button" onClick={() => setShowLocationAlert(false)}>
                Cancel
              </button>
              <button type="button" onClick={handleAllowAccess}>
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
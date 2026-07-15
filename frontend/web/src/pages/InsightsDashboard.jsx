import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getInsightsDashboard } from "../services/InsightsDashboardApi";
import "./InsightsDashboard.css";

const DISTRICTS = [
  {
    id: "uptown",
    apiValue: "uptown",
    label: "Uptown",
    query: "Uptown Manhattan",
  },
  {
    id: "midtown-east",
    apiValue: "midtown_east",
    label: "Midtown East",
    query: "Midtown East Manhattan",
  },
  {
    id: "midtown-west",
    apiValue: "midtown_west",
    label: "Midtown West",
    query: "Midtown West Manhattan",
  },
  {
    id: "downtown",
    apiValue: "downtown",
    label: "Downtown",
    query: "Downtown Manhattan",
  },
];

const EMPTY_DASHBOARD = {
  district: "Midtown East",
  dataMode: "no_data",
  noData: true,
  realTimeDensity: {
    percent: null,
    trend: "No data",
    summary: "No data available",
  },
  quickTriage: {
    waitMinutes: null,
    label: "No data available",
    note: "No current triage recommendation",
  },
  bestTravelWindow: {
    startTime: "",
    endTime: "",
    reason: "No recommended travel window is available",
    ctaLabel: "Check back soon",
  },
  predictionSeries: [],
  historySeries7d: [],
  fastestHubs: [],
  travelTimeSource: "",
};

function clampPercent(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return null;
  }

  return Math.min(100, Math.max(0, number));
}

function normaliseSeries(series) {
  if (!Array.isArray(series)) {
    return [];
  }

  return series
    .map((point) => {
      if (typeof point === "number") {
        return clampPercent(point);
      }

      if (point && typeof point === "object") {
        return clampPercent(
          point.percent ??
            point.value ??
            point.busyness_percent ??
            point.predicted_score
        );
      }

      return null;
    })
    .filter((value) => value !== null);
}

function normaliseHub(rawHub, index) {
  const travelMinutes = Number(
    rawHub.travel_minutes ?? rawHub.travelMinutes ?? 0
  );

  const waitMinutes = Number(
    rawHub.wait_minutes ?? rawHub.waitMinutes ?? 0
  );

  const capacityLabel =
    rawHub.capacity_label ??
    rawHub.capacityLabel ??
    rawHub.flow_status ??
    rawHub.flowStatus ??
    "NO LIVE INFO";

  return {
    venueId:
      rawHub.venue_id ??
      rawHub.venueId ??
      `hub-${index}`,

    rank: Number(rawHub.rank) || index + 1,

    clinicName:
      rawHub.clinic_name ??
      rawHub.venue_name ??
      rawHub.name ??
      "Unnamed facility",

    capacityLabel,

    flowStatus: String(capacityLabel)
      .toLowerCase()
      .replaceAll(" ", "-"),

    travelMinutes: Number.isFinite(travelMinutes)
      ? travelMinutes
      : 0,

    waitMinutes: Number.isFinite(waitMinutes)
      ? waitMinutes
      : 0,

    compositeCost:
      (Number.isFinite(travelMinutes) ? travelMinutes : 0) +
      (Number.isFinite(waitMinutes) ? waitMinutes : 0),

    languageFlags:
      rawHub.language_flags ??
      rawHub.languageFlags ??
      rawHub.languages ??
      [],
  };
}

function normaliseDashboard(rawDashboard, selectedDistrict) {
  if (!rawDashboard || typeof rawDashboard !== "object") {
    return {
      ...EMPTY_DASHBOARD,
      district: selectedDistrict.label,
    };
  }

  const density =
    rawDashboard.real_time_density ??
    rawDashboard.realTimeDensity ??
    {};

  const triage =
    rawDashboard.quick_triage ??
    rawDashboard.quickTriage ??
    {};

  const travelWindow =
    rawDashboard.best_travel_window ??
    rawDashboard.bestTravelWindow ??
    {};

  const predictionSeries = normaliseSeries(
    rawDashboard.prediction_series ??
      rawDashboard.predictionSeries
  );

  const historySeries7d = normaliseSeries(
    rawDashboard.history_series_7d ??
      rawDashboard.historySeries7d
  );

  const rawHubs =
    rawDashboard.fastest_hubs ??
    rawDashboard.fastestHubs ??
    [];

  const fastestHubs = Array.isArray(rawHubs)
    ? rawHubs.map(normaliseHub)
    : [];

  const densityTrend = String(
    density.trend ?? ""
  ).toLowerCase();

  const densityLabel = String(
    density.trend_label ??
      density.summary ??
      density.label ??
      ""
  ).toLowerCase();

  const triageLabel = String(
    triage.label ?? ""
  ).toLowerCase();

  const backendSaysNoData =
    densityTrend.includes("no data") ||
    densityLabel.includes("no data") ||
    triageLabel.includes("no data");

  const noData =
    Boolean(
      rawDashboard.no_data ??
        rawDashboard.noData ??
        rawDashboard.status === "no_data"
    ) ||
    backendSaysNoData ||
    (
      predictionSeries.length === 0 &&
      historySeries7d.length === 0 &&
      fastestHubs.length === 0
    );

  const densityPercent = backendSaysNoData
    ? null
    : clampPercent(density.percent);

  const waitMinutes = triageLabel.includes("no data")
    ? null
    : (
        triage.wait_minutes ??
        triage.waitMinutes ??
        null
      );

  return {
    district:
      rawDashboard.district ??
      selectedDistrict.label,

    dataMode:
      rawDashboard.data_mode ??
      rawDashboard.dataMode ??
      "unknown",

    noData,

    realTimeDensity: {
      percent: densityPercent,

      trend:
        density.trend ??
        density.trend_label ??
        "No data",

      summary:
        density.summary ??
        density.trend_label ??
        density.label ??
        "Current facility utilisation",
    },

    quickTriage: {
      waitMinutes,

      label:
        triage.label ??
        triage.venue_name ??
        "No data available",

      note:
        triage.note ??
        triage.summary ??
        triage.venue_name ??
        "No current triage recommendation",
    },

    bestTravelWindow: {
      startTime:
        travelWindow.start_time ??
        travelWindow.startTime ??
        travelWindow.start ??
        "",

      endTime:
        travelWindow.end_time ??
        travelWindow.endTime ??
        travelWindow.end ??
        "",

      reason:
        travelWindow.reason ??
        travelWindow.summary ??
        "No recommended travel window is available",

      ctaLabel:
        travelWindow.cta_label ??
        travelWindow.ctaLabel ??
        "Plan Route",
    },

    predictionSeries,
    historySeries7d,
    fastestHubs,

    travelTimeSource:
      rawDashboard.travel_time_source ??
      rawDashboard.travelTimeSource ??
      "",
  };
}

function getSavedLocation() {
  try {
    const storedLocation = JSON.parse(
      localStorage.getItem("clearPathUserLocation") ||
        "null"
    );

    const latitude = Number(
      storedLocation?.lat ??
        storedLocation?.latitude
    );

    const longitude = Number(
      storedLocation?.lng ??
        storedLocation?.lon ??
        storedLocation?.longitude
    );

    if (
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
    ) {
      return {
        latitude,
        longitude,
      };
    }
  } catch (error) {
    console.error(
      "Could not read the saved location:",
      error
    );
  }

  return {};
}

function MiniLineChart({ values, mode }) {
  const width = 620;
  const height = 220;
  const padding = 26;

  if (!Array.isArray(values) || values.length === 0) {
    return (
      <div className="insights-chart-empty">
        <strong>No chart data available</strong>

        <p>
          The backend did not return a series for this
          district.
        </p>
      </div>
    );
  }

  const points = values.map((value, index) => {
    const x =
      padding +
      (index * (width - padding * 2)) /
        Math.max(values.length - 1, 1);

    const y =
      height -
      padding -
      (value / 100) * (height - padding * 2);

    return {
      x,
      y,
      value,
    };
  });

  const linePoints = points
    .map((point) => `${point.x},${point.y}`)
    .join(" ");

  const areaPoints = [
    `${points[0].x},${height - padding}`,
    ...points.map(
      (point) => `${point.x},${point.y}`
    ),
    `${points.at(-1).x},${height - padding}`,
  ].join(" ");

  const xLabels =
    mode === "prediction"
      ? ["09:00", "12:00", "15:00", "18:00", "21:00"]
      : [
          "Mon",
          "Tue",
          "Wed",
          "Thu",
          "Fri",
          "Sat",
          "Sun",
        ];

  return (
    <div className="insights-chart-wrap">
      <svg
        className="insights-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={
          mode === "prediction"
            ? "12-hour predictive capacity curve"
            : "7-day historical baseline trend"
        }
      >
        <defs>
          <linearGradient
            id="chartFill"
            x1="0"
            x2="0"
            y1="0"
            y2="1"
          >
            <stop
              offset="0%"
              stopColor="#0052e0"
              stopOpacity="0.22"
            />

            <stop
              offset="100%"
              stopColor="#0052e0"
              stopOpacity="0.02"
            />
          </linearGradient>
        </defs>

        {[0, 25, 50, 75, 100].map((tick) => {
          const y =
            height -
            padding -
            (tick / 100) * (height - padding * 2);

          return (
            <g key={tick}>
              <line
                x1={padding}
                x2={width - padding}
                y1={y}
                y2={y}
                className="chart-grid-line"
              />

              <text
                x={4}
                y={y + 4}
                className="chart-axis-label"
              >
                {tick}%
              </text>
            </g>
          );
        })}

        <polygon
          points={areaPoints}
          fill="url(#chartFill)"
        />

        <polyline
          points={linePoints}
          className="chart-line"
        />

        {points.map((point) => (
          <circle
            key={`${point.x}-${point.y}`}
            cx={point.x}
            cy={point.y}
            r="3"
            className="chart-point"
          />
        ))}
      </svg>

      <div className="chart-x-labels">
        {xLabels.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
    </div>
  );
}

function MetricCard({
  type = "default",
  eyebrow,
  title,
  value,
  meta,
  icon,
  children,
}) {
  return (
    <section className={`insight-metric-card ${type}`}>
      <div className="metric-card-top">
        <span>{eyebrow}</span>

        <span className="metric-card-icon">
          {icon}
        </span>
      </div>

      <div className="metric-value-row">
        <strong>{value}</strong>

        {meta && <span>{meta}</span>}
      </div>

      <h3>{title}</h3>

      {children}
    </section>
  );
}

function InsightsDashboard() {
  const navigate = useNavigate();

  const [selectedDistrictId, setSelectedDistrictId] =
    useState("midtown-east");

  const [chartMode, setChartMode] =
    useState("prediction");

  const [dashboardData, setDashboardData] =
    useState(EMPTY_DASHBOARD);

  const [isLoading, setIsLoading] = useState(true);

  const [isRefreshing, setIsRefreshing] =
    useState(false);

  const [error, setError] = useState("");

  const selectedDistrict = useMemo(
    () =>
      DISTRICTS.find(
        (district) =>
          district.id === selectedDistrictId
      ) ?? DISTRICTS[1],
    [selectedDistrictId]
  );

  const loadDashboard = useCallback(
    async ({ silent = false } = {}) => {
      try {
        const response = await getInsightsDashboard({
          district: selectedDistrict.apiValue,
          ...getSavedLocation(),
        });

        const normalisedData = normaliseDashboard(
          response,
          selectedDistrict
        );

        setDashboardData(normalisedData);
        setError("");

        setChartMode((currentMode) => {
          if (
            currentMode === "history" &&
            normalisedData.historySeries7d.length === 0
          ) {
           return "prediction";
          }

          if (
            currentMode === "prediction" &&
            normalisedData.predictionSeries.length === 0 &&
            normalisedData.historySeries7d.length > 0
          ) {
            return "history";
          }

          return currentMode;
        });
      } catch (loadError) {
        console.error(
          "Failed to load insights dashboard:",
          loadError
        );

        setError(
          loadError.message ||
            "Could not load dashboard insights."
        );

        if (!silent) {
          setDashboardData({
            ...EMPTY_DASHBOARD,
            district: selectedDistrict.label,
          });
        }
      } finally {
        if (silent) {
          setIsRefreshing(false);
        } else {
          setIsLoading(false);
        }
      }
    },
    [selectedDistrict]
  );

 useEffect(() => {
  const initialLoadTimeout = window.setTimeout(() => {
    void loadDashboard();
  }, 0);

  const refreshInterval = window.setInterval(() => {
    setIsRefreshing(true);
    void loadDashboard({ silent: true });
  }, 30000);

  return () => {
    window.clearTimeout(initialLoadTimeout);
    window.clearInterval(refreshInterval);
  };
}, [loadDashboard]);

  const chartValues =
    chartMode === "prediction"
      ? dashboardData.predictionSeries
      : dashboardData.historySeries7d;

  const sortedHubs = useMemo(
    () =>
      dashboardData.fastestHubs
        .slice()
        .sort((firstHub, secondHub) => {
          if (firstHub.rank !== secondHub.rank) {
            return firstHub.rank - secondHub.rank;
          }

          return (
            firstHub.compositeCost -
            secondHub.compositeCost
          );
        }),
    [dashboardData.fastestHubs]
  );

  const densityValue =
    dashboardData.realTimeDensity.percent === null
      ? "—"
      : `${dashboardData.realTimeDensity.percent}%`;

  const triageValue =
    dashboardData.quickTriage.waitMinutes === null
      ? "Unavailable"
      : `${dashboardData.quickTriage.waitMinutes} min wait`;

  const travelWindowValue =
    dashboardData.bestTravelWindow.startTime &&
    dashboardData.bestTravelWindow.endTime
      ? `${dashboardData.bestTravelWindow.startTime} - ${dashboardData.bestTravelWindow.endTime}`
      : "Unavailable";

  function handleDistrictChange(districtId) {
    if (districtId === selectedDistrictId) {
      return;
    }

    setIsLoading(true);
    setError("");
    setSelectedDistrictId(districtId);
  }

  function handleRetry() {
    setIsLoading(true);
    setError("");
    void loadDashboard();
  }

  function handlePlanRoute() {
    navigate("/map", {
      state: {
        district: dashboardData.district,
        query: selectedDistrict.query,
      },
    });
  }

  function handleHubDirections(hub) {
    localStorage.setItem(
      "clearPathDirectionsDestination",
      hub.venueId
    );

    navigate("/map", {
      state: {
        venueId: hub.venueId,
        destination: hub.clinicName,
      },
    });
  }

  return (
    <main className="insights-page">
      <section className="district-scope-bar">
        <span>DISTRICT VIEW:</span>

        <div className="district-filter-row">
          {DISTRICTS.map((district) => (
            <button
              key={district.id}
              type="button"
              className={
                selectedDistrictId === district.id
                  ? "active"
                  : undefined
              }
              onClick={() =>
                handleDistrictChange(district.id)
              }
            >
              {district.label}
            </button>
          ))}
        </div>
      </section>

      <section className="insights-dashboard-shell">
        <header className="insights-header">
          <div>
            <h1>Manhattan Overview</h1>

            <p>
              Real-time facility utilization and demand
              routing.
            </p>
          </div>

          <div className="insights-data-status">
            {isRefreshing && <span>Refreshing…</span>}

            {dashboardData.dataMode &&
              dashboardData.dataMode !== "unknown" && (
                <span>
                  Data source: {dashboardData.dataMode}
                </span>
              )}
          </div>
        </header>

        {error && (
          <section
            className="insights-api-message"
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

        {isLoading ? (
          <section className="insights-empty-state">
            <h2>Loading district insights...</h2>

            <p>
              Retrieving live density, travel windows and
              facility rankings.
            </p>
          </section>
        ) : (
          <>
            {dashboardData.noData && !error && (
              <section className="insights-api-message">
                <p>
                  No live analytics are currently available
                  for {dashboardData.district}. Empty
                  sections are shown below.
                </p>
              </section>
            )}

            <section className="insights-metric-grid">
              <MetricCard
                type="density"
                eyebrow="REAL-TIME DENSITY"
                icon="⌘"
                value={densityValue}
                meta={dashboardData.realTimeDensity.trend}
                title={
                  dashboardData.realTimeDensity.summary
                }
              />

              <MetricCard
                type="triage"
                eyebrow="QUICK TRIAGE DEMAND"
                icon="✱"
                value={triageValue}
                title={dashboardData.quickTriage.note}
              >
                <span className="clinic-chip">
                  {dashboardData.quickTriage.label}
                </span>
              </MetricCard>

              <MetricCard
                type="travel"
                eyebrow="BEST TRAVEL WINDOW"
                icon="◷"
                value={travelWindowValue}
                title={
                  dashboardData.bestTravelWindow.reason
                }
              >
                <button
                  type="button"
                  className="route-link-button"
                  onClick={handlePlanRoute}
                >
                  {
                    dashboardData.bestTravelWindow
                      .ctaLabel
                  }{" "}
                  →
                </button>
              </MetricCard>
            </section>

            <section className="insights-main-grid">
              <section className="prediction-panel">
                <div className="prediction-header">
                  <div>
                    <h2>
                      12-hour busyness prediction
                    </h2>

                    <p>
                      Predicted facility density for the
                      next 12 hours in{" "}
                      {dashboardData.district}.
                    </p>
                  </div>

                  <div
                    className="chart-toggle"
                    aria-label="Chart mode selector"
                  >
                    <button
                      type="button"
                      className={
                        chartMode === "prediction"
                          ? "active"
                          : undefined
                      }
                      disabled={
                        dashboardData.predictionSeries
                          .length === 0
                      }
                      onClick={() =>
                        setChartMode("prediction")
                      }
                    >
                      12-Hour Predicted
                    </button>

                    <button
                      type="button"
                      className={
                        chartMode === "history"
                          ? "active"
                          : undefined
                      }
                      disabled={
                        dashboardData.historySeries7d
                          .length === 0
                      }
                      onClick={() =>
                        setChartMode("history")
                      }
                    >
                      7-Day History
                    </button>
                  </div>
                </div>

                <MiniLineChart
                  values={chartValues}
                  mode={chartMode}
                />

                <div className="chart-legend">
                  <span />

                  {chartMode === "prediction"
                    ? "PREDICTED DENSITY"
                    : "HISTORICAL BASELINE"}
                </div>
              </section>

              <aside className="fastest-hubs-card">
                <div className="leaderboard-heading">
                  <div>
                    <span>Top 3</span>

                    <h2>Fastest Hubs</h2>
                  </div>

                  <p>
                    Ranked by combined wait time + transit
                    from your location.
                  </p>
                </div>

                {dashboardData.travelTimeSource && (
                  <p className="travel-source-note">
                    Travel source:{" "}
                    {dashboardData.travelTimeSource}
                  </p>
                )}

                <div className="leaderboard-table-head">
                  <span>Clinic Hub</span>
                  <span>Capacity</span>
                  <span>Time</span>
                </div>

                {sortedHubs.length === 0 ? (
                  <div className="fastest-hubs-empty">
                    <strong>
                      No facility rankings available
                    </strong>

                    <p>
                      Rankings will appear when the backend
                      returns facility data.
                    </p>
                  </div>
                ) : (
                  <ol className="fastest-hubs-list">
                    {sortedHubs
                      .slice(0, 3)
                      .map((hub) => (
                        <li key={hub.venueId}>
                          <button
                            type="button"
                            className="hub-route-button"
                            onClick={() =>
                              handleHubDirections(hub)
                            }
                            aria-label={`Get directions to ${hub.clinicName}`}
                          >
                            <div className="hub-name-block">
                              <strong>
                                {hub.clinicName}
                              </strong>

                              <div className="language-flags">
                                {hub.languageFlags.map(
                                  (flag) => (
                                    <span key={flag}>
                                      {flag}
                                    </span>
                                  )
                                )}
                              </div>

                              <small>
                                {hub.capacityLabel}
                              </small>
                            </div>

                            <div
                              className="capacity-bar"
                              aria-hidden="true"
                            >
                              <span
                                className={
                                  hub.flowStatus
                                }
                              />
                            </div>

                            <strong className="hub-time">
                              {hub.travelMinutes}m
                            </strong>
                          </button>
                        </li>
                      ))}
                  </ol>
                )}
              </aside>
            </section>
          </>
        )}
      </section>
    </main>
  );
}

export default InsightsDashboard;
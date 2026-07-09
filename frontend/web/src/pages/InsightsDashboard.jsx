import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  DISTRICTS,
  INSIGHTS_DASHBOARD_DATA,
} from "../data/insightsDashboard";
import "./InsightsDashboard.css";

function MiniLineChart({ values, mode }) {
  const width = 620;
  const height = 220;
  const padding = 26;

  const points = values.map((value, index) => {
    const x =
      padding + (index * (width - padding * 2)) / Math.max(values.length - 1, 1);
    const y = height - padding - (value / 100) * (height - padding * 2);

    return { x, y, value };
  });

  const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const areaPoints = [
    `${points[0].x},${height - padding}`,
    ...points.map((point) => `${point.x},${point.y}`),
    `${points[points.length - 1].x},${height - padding}`,
  ].join(" ");

  const xLabels =
    mode === "prediction"
      ? ["09:00", "12:00", "15:00", "18:00", "21:00"]
      : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

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
          <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#0052e0" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#0052e0" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {[0, 25, 50, 75, 100].map((tick) => {
          const y = height - padding - (tick / 100) * (height - padding * 2);

          return (
            <g key={tick}>
              <line
                x1={padding}
                x2={width - padding}
                y1={y}
                y2={y}
                className="chart-grid-line"
              />
              <text x={4} y={y + 4} className="chart-axis-label">
                {tick}%
              </text>
            </g>
          );
        })}

        <polygon points={areaPoints} fill="url(#chartFill)" />
        <polyline points={linePoints} className="chart-line" />

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
        <span className="metric-card-icon">{icon}</span>
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

  const [selectedDistrictId, setSelectedDistrictId] = useState("midtown-east");
  const [chartMode, setChartMode] = useState("prediction");

  const selectedDistrict = useMemo(
    () => DISTRICTS.find((district) => district.id === selectedDistrictId),
    [selectedDistrictId]
  );

  const dashboardData = INSIGHTS_DASHBOARD_DATA[selectedDistrictId];

  const chartValues =
    chartMode === "prediction"
      ? dashboardData.predictionSeries
      : dashboardData.historySeries7d;

  function handleDistrictChange(districtId) {
    setSelectedDistrictId(districtId);

    const nextMode = INSIGHTS_DASHBOARD_DATA[districtId].chartMode;
    setChartMode(nextMode === "history" ? "history" : "prediction");
  }

  function handlePlanRoute() {
    navigate("/map", {
      state: {
        district: dashboardData.district,
        query: selectedDistrict.query,
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
                selectedDistrictId === district.id ? "active" : undefined
              }
              onClick={() => handleDistrictChange(district.id)}
            >
              {district.label}
            </button>
          ))}
        </div>
      </section>

      <section className="insights-dashboard-shell">
        <header className="insights-header">
          <h1>Manhattan Overview</h1>
          <p>Real-time facility utilization and demand routing.</p>
        </header>

        <section className="insights-metric-grid">
          <MetricCard
            type="density"
            eyebrow="REAL-TIME DENSITY"
            icon="⌘"
            value={`${dashboardData.realTimeDensity.percent}%`}
            meta={dashboardData.realTimeDensity.trend}
            title={dashboardData.realTimeDensity.summary}
          />

          <MetricCard
            type="triage"
            eyebrow="QUICK TRIAGE DEMAND"
            icon="✱"
            value={`${dashboardData.quickTriage.waitMinutes} min wait`}
            title={dashboardData.quickTriage.note}
          >
            <span className="clinic-chip">{dashboardData.quickTriage.label}</span>
          </MetricCard>

          <MetricCard
            type="travel"
            eyebrow="BEST TRAVEL WINDOW"
            icon="◷"
            value={`${dashboardData.bestTravelWindow.startTime} - ${dashboardData.bestTravelWindow.endTime}`}
            title={dashboardData.bestTravelWindow.reason}
          >
            <button
              type="button"
              className="route-link-button"
              onClick={handlePlanRoute}
            >
              {dashboardData.bestTravelWindow.ctaLabel} →
            </button>
          </MetricCard>
        </section>

        <section className="insights-main-grid">
          <section className="prediction-panel">
            <div className="prediction-header">
              <div>
                <h2>12-hour busyness prediction</h2>
                <p>
                  Predicted facility density for the next 12 hours in{" "}
                  {dashboardData.district}.
                </p>
              </div>

              <div className="chart-toggle" aria-label="Chart mode selector">
                <button
                  type="button"
                  className={chartMode === "prediction" ? "active" : undefined}
                  onClick={() => setChartMode("prediction")}
                >
                  12-Hour Predicted
                </button>

                <button
                  type="button"
                  className={chartMode === "history" ? "active" : undefined}
                  onClick={() => setChartMode("history")}
                >
                  7-Day History
                </button>
              </div>
            </div>

            <MiniLineChart values={chartValues} mode={chartMode} />

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
              <p>Ranked by combined wait time + transit from your location.</p>
            </div>

            <div className="leaderboard-table-head">
              <span>Clinic Hub</span>
              <span>Capacity</span>
              <span>Time</span>
            </div>

            <ol className="fastest-hubs-list">
              {dashboardData.fastestHubs
                .slice()
                .sort((a, b) => a.compositeCost - b.compositeCost)
                .map((hub) => (
                  <li key={hub.venueId}>
                    <div className="hub-name-block">
                      <strong>{hub.clinicName}</strong>

                      <div className="language-flags">
                        {hub.languageFlags.map((flag) => (
                          <span key={flag}>{flag}</span>
                        ))}
                      </div>

                      <small>{hub.capacityLabel}</small>
                    </div>

                    <div className="capacity-bar" aria-hidden="true">
                      <span className={hub.flowStatus} />
                    </div>

                    <strong className="hub-time">{hub.travelMinutes}m</strong>
                  </li>
                ))}
            </ol>
          </aside>
        </section>
      </section>
    </main>
  );
}

export default InsightsDashboard;
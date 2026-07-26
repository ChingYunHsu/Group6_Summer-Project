import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

function getBusynessColor(value) {
  const percent = Number(value);

  if (!Number.isFinite(percent)) {
    return "#0057e7";
  }

  if (percent < 30) {
    return "#22c55e";
  }

  if (percent <= 70) {
    return "#eab308";
  }

  return "#ef4444";
}

function normaliseBusyness(value) {
  const percent = Number(value);

  if (!Number.isFinite(percent)) {
    return 0;
  }

  return Math.min(100, Math.max(0, percent));
}

function BusynessChart({ venues = [] }) {
  const chartData = venues.map((venue) => ({
    id: venue.venue_id ?? venue.id ?? venue.name,
    name: venue.name ?? "Unnamed venue",
    busyness: normaliseBusyness(
      venue.busyness_percent
    ),
  }));

  return (
    <section>
      <h2>Venue Busyness</h2>

      <div style={{ width: "100%", height: 400 }}>
        <ResponsiveContainer>
          <BarChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 20,
            }}
          >
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12 }}
            />

            <YAxis
              label={{
                value: "Busyness (%)",
                angle: -90,
                position: "insideLeft",
              }}
              tick={{ fontSize: 12 }}
              domain={[0, 100]}
            />

            <Tooltip
              formatter={(value) => [
                `${value}%`,
                "Busyness",
              ]}
              contentStyle={{
                backgroundColor: "#f3f4f6",
                border: "1px solid #d1d5db",
                borderRadius: "8px",
                color: "#333",
                boxShadow:
                  "0 2px 8px rgba(0, 0, 0, 0.1)",
              }}
              cursor={{
                fill: "rgba(0, 0, 0, 0.05)",
              }}
            />

            <Bar
              dataKey="busyness"
              radius={[6, 6, 0, 0]}
            >
              {chartData.map((entry) => (
                <Cell
                  key={entry.id}
                  fill={getBusynessColor(
                    entry.busyness
                  )}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default BusynessChart;
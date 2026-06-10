import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

function BusynessChart({ venues }) {
  const chartData = venues.map((venue) => ({
    name: venue.name,
    busyness: venue.busyness_percent,
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
              formatter={(value) => [`${value}%`, "Busyness"]}
              contentStyle={{
                backgroundColor: "#f3f4f6",
                border: "1px solid #d1d5db",
                borderRadius: "8px",
                color: "#333",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
              }}
              cursor={{
                fill: "rgba(0, 0, 0, 0.05)",
              }}
            />

            <Bar
              dataKey="busyness"
              radius={[6, 6, 0, 0]}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={index}
                  fill={
                    entry.busyness < 40
                      ? "#4CAF50" // Green
                      : entry.busyness < 70
                      ? "#FFC107" // Yellow
                      : "#F44336" // Red
                  }
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
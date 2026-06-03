import { VENUES } from "./data/venues";
import { REPORTS } from "./data/reports";

function App() {
  return (
    <div style={{ padding: "20px" }}>
      <h1>ClinicFlow</h1>

      <h2>Summary</h2>
      <p>Total Venues: {VENUES.length}</p>
      <p>Open Venues: {VENUES.filter(v => v.open_now).length}</p>
      <p>Active Reports: {REPORTS.length}</p>

      <h2>Venues</h2>
      {VENUES.map((venue) => (
        <div
          key={venue.venue_id}
          style={{
            border: "1px solid #ccc",
            padding: "10px",
            marginBottom: "10px"
          }}
        >
          <strong>{venue.name}</strong>
          <p>Type: {venue.venue_type}</p>
          <p>Borough: {venue.borough}</p>
          <p>Wait Time: {venue.avg_wait_minutes} mins</p>
          <p>Open: {venue.open_now ? "Yes" : "No"}</p>
        </div>
      ))}

      <h2>Reports</h2>
      {REPORTS.map((report) => (
        <div
          key={report.report_id}
          style={{
            border: "1px solid red",
            padding: "10px",
            marginBottom: "10px"
          }}
        >
          <strong>{report.issue_type}</strong>
          <p>Status: {report.status}</p>
          <p>Confirmations: {report.confirmation_count}</p>
          <p>{report.badge_text}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
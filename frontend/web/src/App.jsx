<<<<<<< HEAD
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import "./styles/tokens.css";
import "./App.css";

import Login from "./pages/Login";
import LiveHelpMap from "./pages/LiveHelpMap";
import InsightsDashboard from "./pages/InsightsDashboard";
import About from "./pages/About";
import UserGuide from "./pages/UserGuide";
import Profile from "./pages/Profile";
import EditProfile from "./pages/EditProfile";
import MedicalCard from "./pages/MedicalCard";

function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <Link to="/" className="logo">ClearPath</Link>

        <nav>
          <Link to="/map">Live Help Map</Link>
          <Link to="/insights">Insights Dashboard</Link>
          <Link to="/about">About Us</Link>
          <Link to="/guide">User Guide</Link>
          <Link to="/profile">Profile</Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/map" element={<LiveHelpMap />} />
        <Route path="/insights" element={<InsightsDashboard />} />
        <Route path="/about" element={<About />} />
        <Route path="/guide" element={<UserGuide />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/profile/edit" element={<EditProfile />} />
        <Route path="/medical-card" element={<MedicalCard />} />
      </Routes>
    </BrowserRouter>
=======
import { VENUES } from "./data/venues";
import { REPORTS } from "./data/reports";
import BusynessChart from "./components/BusynessChart";

function App() {
  return (
    <div style={{ padding: "20px" }}>
      <h1>ClearPath</h1>

      <h2>Summary</h2>
      <p>Total Venues: {VENUES.length}</p>
      <p>Open Venues: {VENUES.filter(v => v.open_now).length}</p>
      <p>Active Reports: {REPORTS.length}</p>
      <BusynessChart venues={VENUES} />

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
>>>>>>> e3d81fe0122ebe7355ce6c24eaf4d10c091a16f1
  );
}

export default App;
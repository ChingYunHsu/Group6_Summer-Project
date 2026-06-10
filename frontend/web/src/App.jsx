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
      <div className="app-shell">
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
      </div>
    </BrowserRouter>
  );
}

export default App;
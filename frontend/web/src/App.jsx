import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
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
import Settings from "./pages/Settings";
import Favourites from "./pages/Favourites";

function App() {
  const [user, setUser] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setOpenDropdown(null);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  function handleLogout() {
    localStorage.removeItem("clearPathUserLocation");
    setUser(null);
    setOpenDropdown(null);
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="app-header">
          <Link to="/" className="logo">
            ClearPath
          </Link>

          <nav className="main-nav">
            <Link to="/map">Live Help Map</Link>
            <Link to="/insights">Insights Dashboard</Link>
            <Link to="/about">About Us</Link>
            <Link to="/guide">User Guide</Link>
          </nav>

          <div className="header-controls" ref={dropdownRef}>
            <div className="dropdown-wrapper">
              <button
                className="header-icon-btn"
                type="button"
                onClick={() =>
                  setOpenDropdown(
                    openDropdown === "language" ? null : "language"
                  )
                }
              >
                🌐
              </button>

              {openDropdown === "language" && (
                <div className="header-dropdown language-dropdown">
                  <button type="button">English (English)</button>
                  <button type="button">Français (French)</button>
                  <button type="button">Español (Spanish)</button>
                  <button type="button">中文 (Chinese)</button>
                  <button type="button">العربية (Arabic)</button>
                </div>
              )}
            </div>

            <div className="dropdown-wrapper">
              <button
                className="avatar-btn"
                type="button"
                onClick={() =>
                  setOpenDropdown(
                    openDropdown === "profile" ? null : "profile"
                  )
                }
              >
                👩🏻‍⚕️
              </button>

              {openDropdown === "profile" && (
                <div className="header-dropdown profile-dropdown">
                  <Link to="/profile" onClick={() => setOpenDropdown(null)}>
                    Profile
                  </Link>
                  <Link to="/favourites" onClick={() => setOpenDropdown(null)}>
                    Favourites
                  </Link>
                  <Link to="/settings" onClick={() => setOpenDropdown(null)}>
                    Settings
                  </Link>
                  <button
                    className="logout-btn"
                    type="button"
                    onClick={handleLogout}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<Login setUser={setUser} />} />
          <Route path="/map" element={<LiveHelpMap />} />
          <Route path="/insights" element={<InsightsDashboard />} />
          <Route path="/about" element={<About />} />
          <Route path="/guide" element={<UserGuide />} />
          <Route path="/profile" element={<Profile user={user} />} />
          <Route path="/profile/edit" element={<EditProfile user={user} />} />
          <Route path="/medical-card" element={<MedicalCard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/favourites" element={<Favourites />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
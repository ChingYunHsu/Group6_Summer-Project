import { useEffect, useRef, useState } from "react";
import clearPathLogo from "./assets/clearpath-logo.png";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import { useTranslation } from "react-i18next";

import "./styles/tokens.css";
import "./purged-styles.css";
import "./i18n";

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

const LANGUAGE_OPTIONS = [
  {
    code: "en",
    label: "English",
  },
  {
    code: "fr",
    label: "Français",
  },
  {
    code: "es",
    label: "Español",
  },
  {
    code: "it",
    label: "Italiano",
  },
  {
    code: "de",
    label: "Deutsch",
  },
  {
    code: "zh",
    label: "中文",
  },
];

function App() {
  const { t, i18n } = useTranslation("common");

  const [user, setUser] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);

  const dropdownRef = useRef(null);

  const currentLanguage =
    i18n.resolvedLanguage?.split("-")[0] || "en";

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setOpenDropdown(null);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClickOutside
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, []);

  function handleLogout() {
    localStorage.removeItem("clearPathUserLocation");

    setUser(null);
    setOpenDropdown(null);
  }

  async function handleLanguageChange(languageCode) {
    try {
      localStorage.setItem(
        "clearpath_language",
        languageCode
      );

      await i18n.changeLanguage(languageCode);
      setOpenDropdown(null);
    } catch (error) {
      console.error(
        "Failed to change language:",
        error
      );
    }
  }

  function getNavLinkClass({ isActive }) {
    return isActive
      ? "nav-link active"
      : "nav-link";
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="app-header">
          <Link to="/" className="logo">
          <img
            src={clearPathLogo}
            alt=""
            aria-hidden="true"
            className="navbar-brand-logo"
          />
            ClearPath
          </Link>

          <nav
            className="main-nav"
            aria-label={t("navigation.mainNavigation")}
          >
            <NavLink
              to="/map"
              className={getNavLinkClass}
            >
              {t("navigation.liveHelpMap")}
            </NavLink>

            <NavLink
              to="/insights"
              className={getNavLinkClass}
            >
              {t("navigation.insightsDashboard")}
            </NavLink>

            <NavLink
              to="/about"
              className={getNavLinkClass}
            >
              {t("navigation.aboutUs")}
            </NavLink>

            <NavLink
              to="/guide"
              className={getNavLinkClass}
            >
              {t("navigation.userGuide")}
            </NavLink>
          </nav>

          <div
            className="header-controls"
            ref={dropdownRef}
          >
            <div className="dropdown-wrapper">
              <button
                className="header-icon-btn"
                type="button"
                aria-label={t(
                  "navigation.changeLanguage",
                  {
                    defaultValue: "Change language",
                  }
                )}
                aria-expanded={
                  openDropdown === "language"
                }
                aria-haspopup="menu"
                onClick={() =>
                  setOpenDropdown((current) =>
                    current === "language"
                      ? null
                      : "language"
                  )
                }
              >
                🌐
              </button>

              {openDropdown === "language" && (
                <div
                  className="header-dropdown language-dropdown"
                  role="menu"
                  aria-label={t(
                    "navigation.changeLanguage",
                    {
                      defaultValue:
                        "Change language",
                    }
                  )}
                >
                  {LANGUAGE_OPTIONS.map(
                    ({ code, label }) => (
                      <button
                        key={code}
                        type="button"
                        role="menuitem"
                        className={
                          currentLanguage === code
                            ? "active-language"
                            : ""
                        }
                        aria-current={
                          currentLanguage === code
                            ? "true"
                            : undefined
                        }
                        onClick={() =>
                          handleLanguageChange(code)
                        }
                      >
                        {label}
                      </button>
                    )
                  )}
                </div>
              )}
            </div>

            <div className="dropdown-wrapper">
              <button
                className="avatar-btn"
                type="button"
                aria-label={t(
                  "navigation.openProfileMenu",
                  {
                    defaultValue:
                      "Open profile menu",
                  }
                )}
                aria-expanded={
                  openDropdown === "profile"
                }
                aria-haspopup="menu"
                onClick={() =>
                  setOpenDropdown((current) =>
                    current === "profile"
                      ? null
                      : "profile"
                  )
                }
              >
                👩🏻‍⚕️
              </button>

              {openDropdown === "profile" && (
                <div
                  className="header-dropdown profile-dropdown"
                  role="menu"
                >
                  <Link
                    to="/profile"
                    role="menuitem"
                    onClick={() =>
                      setOpenDropdown(null)
                    }
                  >
                    {t("navigation.profile", {
                      defaultValue: "Profile",
                    })}
                  </Link>

                  <Link
                    to="/favourites"
                    role="menuitem"
                    onClick={() =>
                      setOpenDropdown(null)
                    }
                  >
                    {t("navigation.favourites", {
                      defaultValue: "Favourites",
                    })}
                  </Link>

                  <Link
                    to="/settings"
                    role="menuitem"
                    onClick={() =>
                      setOpenDropdown(null)
                    }
                  >
                    {t("navigation.settings", {
                      defaultValue: "Settings",
                    })}
                  </Link>

                  <button
                    className="logout-btn"
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                  >
                    {t("navigation.logout", {
                      defaultValue: "Logout",
                    })}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <Routes>
          <Route
            path="/"
            element={<Login setUser={setUser} />}
          />

          <Route
            path="/map"
            element={<LiveHelpMap />}
          />

          <Route
            path="/insights"
            element={<InsightsDashboard />}
          />

          <Route
            path="/about"
            element={<About />}
          />

          <Route
            path="/guide"
            element={<UserGuide />}
          />

          <Route
            path="/profile"
            element={<Profile user={user} />}
          />

          <Route
            path="/profile/edit"
            element={<EditProfile user={user} />}
          />

          <Route
            path="/medical-card"
            element={<MedicalCard />}
          />

          <Route
            path="/settings"
            element={<Settings />}
          />

          <Route
            path="/favourites"
            element={<Favourites />}
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
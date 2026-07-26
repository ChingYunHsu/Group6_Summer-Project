import { useEffect, useRef, useState } from "react";
import clearPathLogo from "./assets/clearpath-logo.png";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useNavigate,
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

const AUTH_MODE_KEY = "auth_mode";
const AUTHENTICATED_MODE = "authenticated";
const GUEST_MODE = "guest";
const LOGGED_OUT_MODE = "logged_out";

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

function AppContent() {
  const { t, i18n } = useTranslation("common");
  const navigate = useNavigate();

  const [user, setUser] = useState(null);

  const [authMode, setAuthMode] = useState(() => {
    return localStorage.getItem(AUTH_MODE_KEY) || LOGGED_OUT_MODE;
  });

  const [openDropdown, setOpenDropdown] = useState(null);

  const dropdownRef = useRef(null);

  const currentLanguage =
    i18n.resolvedLanguage?.split("-")[0] || "en";

  const accessToken =
    localStorage.getItem("access_token");

  const isAuthenticatedUser =
    Boolean(accessToken) &&
    authMode === AUTHENTICATED_MODE;

  const isGuestUser =
    Boolean(accessToken) &&
    authMode === GUEST_MODE;

  /*
   * Authenticated accounts use the map as the application's home page.
   * Guests and logged-out users can use the logo to return to login/register.
   */
  const logoDestination = isAuthenticatedUser
    ? "/map"
    : "/";

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

  /*
   * Keep authentication state synchronised if the session changes
   * in another browser tab.
   */
  useEffect(() => {
    function handleStorageChange(event) {
      if (
        event.key === AUTH_MODE_KEY ||
        event.key === "access_token"
      ) {
        setAuthMode(
          localStorage.getItem(AUTH_MODE_KEY) ||
            LOGGED_OUT_MODE
        );
      }
    }

    window.addEventListener(
      "storage",
      handleStorageChange
    );

    return () => {
      window.removeEventListener(
        "storage",
        handleStorageChange
      );
    };
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem(AUTH_MODE_KEY);
    localStorage.removeItem(
      "clearPathUserLocation"
    );

    setUser(null);
    setAuthMode(LOGGED_OUT_MODE);
    setOpenDropdown(null);

    navigate("/", { replace: true });
  }

  async function handleLanguageChange(
    languageCode
  ) {
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
    <div className="app-shell">
      <header className="app-header">
        <Link
          to={logoDestination}
          className="logo"
          aria-label={
            isAuthenticatedUser
              ? "ClearPath map"
              : "ClearPath login"
          }
        >
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
          aria-label={t(
            "navigation.mainNavigation"
          )}
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
            {t(
              "navigation.insightsDashboard"
            )}
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
                  defaultValue:
                    "Change language",
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
                        handleLanguageChange(
                          code
                        )
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
                    "Open account menu",
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
                {isAuthenticatedUser ? (
                  <>
                    <Link
                      to="/profile"
                      role="menuitem"
                      onClick={() =>
                        setOpenDropdown(null)
                      }
                    >
                      {t(
                        "navigation.profile",
                        {
                          defaultValue:
                            "Profile",
                        }
                      )}
                    </Link>

                    <Link
                      to="/favourites"
                      role="menuitem"
                      onClick={() =>
                        setOpenDropdown(null)
                      }
                    >
                      {t(
                        "navigation.favourites",
                        {
                          defaultValue:
                            "Favourites",
                        }
                      )}
                    </Link>

                    <Link
                      to="/settings"
                      role="menuitem"
                      onClick={() =>
                        setOpenDropdown(null)
                      }
                    >
                      {t(
                        "navigation.settings",
                        {
                          defaultValue:
                            "Settings",
                        }
                      )}
                    </Link>

                    <button
                      className="logout-btn"
                      type="button"
                      role="menuitem"
                      onClick={handleLogout}
                    >
                      {t(
                        "navigation.logout",
                        {
                          defaultValue:
                            "Logout",
                        }
                      )}
                    </button>
                  </>
                ) : (
                  <>
                    {/*
                     * Settings remains available to guests and
                     * logged-out users so that legal and privacy
                     * information is always accessible.
                     */}
                    <Link
                      to="/settings"
                      role="menuitem"
                      onClick={() =>
                        setOpenDropdown(null)
                      }
                    >
                      {t(
                        "navigation.settings",
                        {
                          defaultValue:
                            "Settings",
                        }
                      )}
                    </Link>

                    <Link
                      to="/"
                      role="menuitem"
                      onClick={() =>
                        setOpenDropdown(null)
                      }
                    >
                      {t(
                        "navigation.loginRegister",
                        {
                          defaultValue:
                            "Login / Register",
                        }
                      )}
                    </Link>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <Routes>
        <Route
          path="/"
          element={
            <Login
              setUser={setUser}
              setAuthMode={setAuthMode}
            />
          }
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
          element={
            <EditProfile user={user} />
          }
        />

        <Route
          path="/medical-card"
          element={<MedicalCard />}
        />

        {/*
         * Settings deliberately has no authentication guard.
         * Guests must be able to read legal, privacy and
         * security information.
         */}
        <Route
          path="/settings"
          element={
            <Settings
              isAuthenticatedUser={isAuthenticatedUser}
              isGuestUser={isGuestUser}
              setAuthMode={setAuthMode}
              setUser={setUser}
            />
          }
        />

        <Route
          path="/favourites"
          element={<Favourites />}
        />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
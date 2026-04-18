import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard } from "../api/client";
import { useEffect, useState } from "react";
import { useNarrowHeader } from "../hooks/useNarrowHeader";

const PRIMARY_LINKS = [
  { path: "/posts", label: "Posts" },
  { path: "/tags", label: "Tags" },
  { path: "/users", label: "Users" },
  { path: "/comments", label: "Comments" },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const narrowHeader = useNarrowHeader();
  const [tickerStats, setTickerStats] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    fetchDashboard()
      .then((data) => setTickerStats(data?.stats ?? { failed: true }))
      .catch(() => setTickerStats({ failed: true }));
  }, []);

  useEffect(() => {
    const id = window.requestAnimationFrame(() => setMobileMenuOpen(false));
    return () => window.cancelAnimationFrame(id);
  }, [location.pathname, narrowHeader]);

  useEffect(() => {
    if (!mobileMenuOpen || !narrowHeader) return;
    const onKey = (e) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileMenuOpen, narrowHeader]);

  const handleLogout = async () => {
    await logout();
    navigate("/dashboard");
  };

  const isActive = (path) => {
    if (path === "/posts") return location.pathname.startsWith("/posts");
    if (path === "/tags") return location.pathname.startsWith("/tags");
    if (path === "/users") return location.pathname.startsWith("/users");
    if (path === "/comments") return location.pathname.startsWith("/comments");
    return false;
  };

  const tickerItems = tickerStats && !tickerStats.failed
    ? [
        `${tickerStats.total_posts ?? 0} posts published`,
        `${tickerStats.authors ?? 0} authors active`,
        `${tickerStats.active_tags ?? 0} tags available`,
        `${tickerStats.comments ?? 0} comments total`,
        `${tickerStats.average_depth_words ?? 0} avg word depth`,
        `${tickerStats.total_posts ?? 0} posts published`,
        `${tickerStats.authors ?? 0} authors active`,
        `${tickerStats.active_tags ?? 0} tags available`,
        `${tickerStats.comments ?? 0} comments total`,
        `${tickerStats.average_depth_words ?? 0} avg word depth`,
      ]
    : null;

  const primaryNavList = (variant) => (
    <ul className={variant === "desktop" ? "nb-nav" : "nb-nav-mobile-list"}>
      {PRIMARY_LINKS.map(({ path, label }) => (
        <li key={path}>
          <Link to={path} className={isActive(path) ? "active" : ""}>
            {label}
          </Link>
        </li>
      ))}
    </ul>
  );

  return (
    <>
      <header className="nb-header">
        <div className="nb-header-inner">
          <Link className="nb-brand" to="/dashboard">TheBlog</Link>

          {!narrowHeader && (
            <nav aria-label="Primary" className="nb-primary-desktop">
              {primaryNavList("desktop")}
            </nav>
          )}

          {narrowHeader && (
            <button
              type="button"
              className="nb-menu-toggle"
              aria-expanded={mobileMenuOpen}
              aria-controls="nb-mobile-primary-nav"
              id="nb-menu-toggle"
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              onClick={() => setMobileMenuOpen((o) => !o)}
            >
              <span className="nb-menu-toggle-bars" aria-hidden>
                <span />
                <span />
                <span />
              </span>
            </button>
          )}

          <div className="nb-header-right">
            {user ? (
              <>
                <Link to="/profile" className="nb-user-tag">
                  @{user.username}
                  {user.profile?.role && user.profile.role !== "user" && (
                    <span style={{ marginLeft: "6px", opacity: 0.7 }}>
                      [{user.profile.role}]
                    </span>
                  )}
                </Link>
                <button className="nb-btn-head" onClick={handleLogout} type="button">
                  Logout
                </button>
                <Link
                  to="/posts?create=1"
                  className="nb-btn-head cta"
                  onClick={(e) => {
                    if (location.pathname !== "/posts") return;
                    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
                      return;
                    }
                    e.preventDefault();
                    navigate("/posts?create=1", { replace: true });
                  }}
                >
                  + New Post
                </Link>
              </>
            ) : (
              <>
                <Link to="/login" className="nb-btn-head">
                  Login
                </Link>
                <Link to="/register" className="nb-btn-head cta">
                  Register
                </Link>
              </>
            )}
          </div>
        </div>

        {narrowHeader && mobileMenuOpen && (
          <div className="nb-mobile-drawer" id="nb-mobile-primary-nav">
            <nav aria-label="Primary">{primaryNavList("mobile")}</nav>
          </div>
        )}
      </header>

      {tickerItems && (
        <div className="nb-ticker">
          <div className="nb-ticker-inner">
            {tickerItems.map((item, i) => (
              <span key={i} className="nb-ticker-item">{item}</span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

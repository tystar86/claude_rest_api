import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard } from "../api/client";
import { useEffect, useRef, useState } from "react";
import { useNarrowHeader } from "../hooks/useNarrowHeader";

const PRIMARY_LINKS = [
  { path: "/posts", label: "Posts" },
  { path: "/tags", label: "Tags" },
  { path: "/users", label: "Users" },
  { path: "/comments", label: "Comments" },
];

function truncTickerLabel(text, max) {
  if (text == null || text === "") return "";
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

function fmtTickerWhen(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Build scrolling headline lines from dashboard `activity` (news-style). */
function buildTickerLinesFromDashboard(data) {
  if (!data || data.failed) return null;
  const a = data.activity ?? {};
  const lines = [];
  if (a.latest_post_title && a.latest_post_at) {
    const title = truncTickerLabel(a.latest_post_title, 48);
    lines.push(`Latest post "${title}" published on ${fmtTickerWhen(a.latest_post_at)}`);
  }
  if (a.latest_comment_author && a.latest_comment_at) {
    const postBit = a.latest_comment_post_title
      ? ` on "${truncTickerLabel(a.latest_comment_post_title, 32)}"`
      : "";
    lines.push(
      `Latest comment by @${a.latest_comment_author}${postBit} on ${fmtTickerWhen(a.latest_comment_at)}`,
    );
  }
  if (a.latest_user_username && a.latest_user_joined_at) {
    lines.push(
      `New member @${a.latest_user_username} joined on ${fmtTickerWhen(a.latest_user_joined_at)}`,
    );
  }
  if (lines.length === 0) {
    lines.push(
      "Site news will appear here once there are posts, comments, and new members.",
    );
  }
  return [...lines, ...lines];
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const narrowHeader = useNarrowHeader();
  const [tickerSource, setTickerSource] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const prevPathRef = useRef(null);
  const prevNarrowRef = useRef(null);

  useEffect(() => {
    fetchDashboard()
      .then((data) => setTickerSource(data ?? { failed: true }))
      .catch(() => setTickerSource({ failed: true }));
  }, []);

  // Close the mobile drawer only when route or breakpoint mode actually changes — not on every
  // mount tick. requestAnimationFrame(close) raced with open clicks in some CI/jsdom timings.
  useEffect(() => {
    const path = location.pathname;
    const narrow = narrowHeader;
    if (prevPathRef.current === null && prevNarrowRef.current === null) {
      prevPathRef.current = path;
      prevNarrowRef.current = narrow;
      return;
    }
    const pathChanged = prevPathRef.current !== path;
    const narrowChanged = prevNarrowRef.current !== narrow;
    prevPathRef.current = path;
    prevNarrowRef.current = narrow;
    if (pathChanged || narrowChanged) {
      queueMicrotask(() => setMobileMenuOpen(false));
    }
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

  const tickerItems = buildTickerLinesFromDashboard(tickerSource);

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

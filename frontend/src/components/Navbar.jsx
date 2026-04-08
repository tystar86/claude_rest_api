import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard } from "../api/client";
import { useEffect, useState } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [tickerStats, setTickerStats] = useState(null);

  useEffect(() => {
    fetchDashboard()
      .then((data) => setTickerStats(data?.stats ?? { failed: true }))
      .catch(() => setTickerStats({ failed: true }));
  }, []);

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
        `${tickerStats.total_posts ?? 0} posts published`,
        `${tickerStats.authors ?? 0} authors active`,
        `${tickerStats.active_tags ?? 0} tags available`,
        `${tickerStats.comments ?? 0} comments total`,
      ]
    : null;

  return (
    <>
      <header className="nb-header">
        <div className="nb-header-inner">
          <Link className="nb-brand" to="/dashboard">TheBlog</Link>

          <nav aria-label="Primary">
            <ul className="nb-nav">
              <li>
                <Link to="/posts" className={isActive("/posts") ? "active" : ""}>
                  Posts
                </Link>
              </li>
              <li>
                <Link to="/tags" className={isActive("/tags") ? "active" : ""}>
                  Tags
                </Link>
              </li>
              <li>
                <Link to="/users" className={isActive("/users") ? "active" : ""}>
                  Users
                </Link>
              </li>
              <li>
                <Link to="/comments" className={isActive("/comments") ? "active" : ""}>
                  Comments
                </Link>
              </li>
            </ul>
          </nav>

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
                <Link to="/posts" className="nb-btn-head cta">
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

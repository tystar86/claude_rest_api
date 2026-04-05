import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchUsers } from "../api/client";
import RoleBadge from "../components/RoleBadge";

export default function UserList() {
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetchUsers(1)
      .then((res) => {
        setItems(res.results);
        setTotal(res.count);
        setHasMore(res.page < res.total_pages);
        setPage(1);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
        setHasMore(false);
        setFetchError(true);
      });
  }, []);

  const loadMore = () => {
    const next = page + 1;
    setLoadingMore(true);
    fetchUsers(next)
      .then((res) => {
        setItems((prev) => [...prev, ...res.results]);
        setHasMore(res.page < res.total_pages);
        setPage(next);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  if (items === null) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  if (fetchError) return (
    <div className="nb-layout-full">
      <div className="nb-error" style={{ padding: "40px 32px" }}>
        Failed to load users. Please refresh the page.
      </div>
    </div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{total}</div>
        <div>
          <div className="nb-hero-label">Authors registered</div>
          <div className="nb-hero-desc">Meet the engineers writing on this platform.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">All Users</span>
        <span className="nb-section-count">{items.length} loaded</span>
      </div>

      {/* User rows */}
      {items.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No users yet.
        </div>
      )}

      {items.map((u, index) => {
        const num = String(index + 1).padStart(2, "0");
        return (
          <Link key={u.id} to={`/users/${u.username}`} className="nb-post-item">
            <div className="nb-post-num">{num}</div>
            <div className="nb-post-body">
              <div className="nb-post-title">{u.username}</div>
              <div className="nb-post-meta">
                {u.email && <span>{u.email}</span>}
                <span className="nb-post-meta-sep">·</span>
                <span>
                  Joined {new Date(u.date_joined).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </span>
                <span className="nb-post-meta-sep">·</span>
                <span>{u.post_count} post{u.post_count !== 1 ? "s" : ""}</span>
              </div>
            </div>
            <div className="nb-post-right">
              <RoleBadge role={u.profile?.role} />
              {(!u.profile?.role || u.profile?.role === "user") && (
                <span className="nb-status-draft">User</span>
              )}
            </div>
          </Link>
        );
      })}

      {/* Load More */}
      {hasMore && (
        <button
          className="nb-btn nb-btn-full"
          onClick={loadMore}
          disabled={loadingMore}
          style={{ marginTop: "16px" }}
        >
          {loadingMore ? "Loading…" : "Load More"}
        </button>
      )}

    </div>
  );
}

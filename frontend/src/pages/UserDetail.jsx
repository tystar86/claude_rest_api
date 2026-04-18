import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchUser } from "../api/client";
import RoleBadge from "../components/RoleBadge";
import StatusBadge from "../components/StatusBadge";

export default function UserDetail() {
  const { username } = useParams();
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [userInfo, setUserInfo] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetchUser(username, 1)
      .then((res) => {
        setNotFound(false);
        setFetchError(false);
        setItems(res.results);
        setTotal(res.count);
        setUserInfo(res.user);
        setHasMore(res.page < res.total_pages);
        setPage(1);
      })
      .catch((err) => {
        setItems([]);
        if (err?.response?.status === 404) setNotFound(true);
        else setFetchError(true);
      });
  }, [username]);

  const loadMore = () => {
    const next = page + 1;
    setLoadingMore(true);
    fetchUser(username, next)
      .then((res) => {
        setItems((prev) => [...prev, ...res.results]);
        setHasMore(res.page < res.total_pages);
        setPage(next);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  if (notFound) return (
    <div className="nb-layout-full"><div className="nb-error">User not found.</div></div>
  );
  if (fetchError) return (
    <div className="nb-layout-full"><div className="nb-error">Failed to load user. Please try again.</div></div>
  );
  if (items === null || userInfo === null) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  return (
    <div className="nb-layout" style={{ gridTemplateColumns: "280px 1fr" }}>

      {/* Sidebar / user card */}
      <aside className="nb-sidebar" style={{ borderRight: "var(--border)" }}>
        <div className="nb-sidebar-block" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "60px", lineHeight: 1, marginBottom: "12px" }}>
            <i className="bi bi-person-square" style={{ color: "var(--black)" }} />
          </div>
          <div className="nb-username">{userInfo.username}</div>
          {userInfo.email && (
            <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.55, marginBottom: "10px" }}>
              {userInfo.email}
            </div>
          )}
          <div style={{ marginBottom: "10px" }}>
            <RoleBadge role={userInfo.profile?.role} />
            {(!userInfo.profile?.role || userInfo.profile?.role === "user") && (
              <span className="nb-status-draft">User</span>
            )}
          </div>
          {userInfo.profile?.bio && (
            <div style={{ fontSize: "13px", opacity: 0.7, marginTop: "12px", lineHeight: 1.5 }}>
              {userInfo.profile.bio}
            </div>
          )}
        </div>

        <div className="nb-sidebar-block">
          <div className="nb-sidebar-head">Info</div>
          <div className="nb-stat-row">
            <span>Posts</span>
            <span>{total}</span>
          </div>
          <div className="nb-stat-row">
            <span>Role</span>
            <span>{userInfo.profile?.role ?? "user"}</span>
          </div>
          <div className="nb-stat-row">
            <span>Joined</span>
            <span style={{ fontSize: "12px" }}>
              {new Date(userInfo.date_joined).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
            </span>
          </div>
        </div>

        <div style={{ padding: "16px var(--nb-copy-pad-x)" }}>
          <Link to="/users" style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--black)", textDecoration: "underline" }}>
            ← All Users
          </Link>
        </div>
      </aside>

      {/* Posts column */}
      <main className="nb-main">
        <div className="nb-section-bar">
          <span className="nb-section-title">Posts by {userInfo.username}</span>
          <span className="nb-section-count">{total} total</span>
        </div>

        {items.length === 0 && (
          <div style={{ padding: "40px var(--nb-copy-pad-x)", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
            No posts yet.
          </div>
        )}

        {items.map((post, index) => {
          const num = String(index + 1).padStart(2, "0");
          return (
            <Link key={post.id} to={`/posts/${post.slug}`} className="nb-post-item">
              <div className="nb-post-num">{num}</div>
              <div className="nb-post-body">
                <div className="nb-post-title">{post.title}</div>
                <div className="nb-post-meta">
                  <span>{new Date(post.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                </div>
                {post.tags?.length > 0 && (
                  <div className="nb-post-tags">
                    {post.tags.map((tag) => (
                      <span key={tag.id} className="nb-tag-box">{tag.name}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="nb-post-right">
                <StatusBadge status={post.status} />
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
      </main>

    </div>
  );
}

import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { fetchUser } from "../api/client";
import Pagination from "../components/Pagination";
import RoleBadge from "../components/RoleBadge";
import StatusBadge from "../components/StatusBadge";

export default function UserDetail() {
  const { username } = useParams();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    fetchUser(username, page)
      .then((result) => { setNotFound(false); setFetchError(false); setData(result); })
      .catch((err) => {
        setData(null);
        if (err?.response?.status === 404) setNotFound(true);
        else setFetchError(true);
      });
  }, [username, page]);

  if (notFound) return (
    <div className="nb-layout-full"><div className="nb-error">User not found.</div></div>
  );
  if (fetchError) return (
    <div className="nb-layout-full"><div className="nb-error">Failed to load user. Please try again.</div></div>
  );
  if (!data) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  const { user } = data;

  return (
    <div className="nb-layout" style={{ gridTemplateColumns: "280px 1fr" }}>

      {/* Sidebar / user card */}
      <aside className="nb-sidebar" style={{ borderRight: "var(--border)" }}>
        <div className="nb-sidebar-block" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "60px", lineHeight: 1, marginBottom: "12px" }}>
            <i className="bi bi-person-square" style={{ color: "var(--black)" }} />
          </div>
          <div className="nb-username">{user.username}</div>
          {user.email && (
            <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.55, marginBottom: "10px" }}>
              {user.email}
            </div>
          )}
          <div style={{ marginBottom: "10px" }}>
            <RoleBadge role={user.profile?.role} />
            {(!user.profile?.role || user.profile?.role === "user") && (
              <span className="nb-status-draft">User</span>
            )}
          </div>
          {user.profile?.bio && (
            <div style={{ fontSize: "13px", opacity: 0.7, marginTop: "12px", lineHeight: 1.5 }}>
              {user.profile.bio}
            </div>
          )}
        </div>

        <div className="nb-sidebar-block">
          <div className="nb-sidebar-head">Info</div>
          <div className="nb-stat-row">
            <span>Posts</span>
            <span>{data.count}</span>
          </div>
          <div className="nb-stat-row">
            <span>Role</span>
            <span>{user.profile?.role ?? "user"}</span>
          </div>
          <div className="nb-stat-row">
            <span>Joined</span>
            <span style={{ fontSize: "12px" }}>
              {new Date(user.date_joined).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
            </span>
          </div>
        </div>

        <div style={{ padding: "16px 24px" }}>
          <Link to="/users" style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--black)", textDecoration: "underline" }}>
            ← All Users
          </Link>
        </div>
      </aside>

      {/* Posts column */}
      <main className="nb-main">
        <div className="nb-section-bar">
          <span className="nb-section-title">Posts by {user.username}</span>
          <span className="nb-section-count">{data.count} total</span>
        </div>

        {data.results.length === 0 && (
          <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
            No posts yet.
          </div>
        )}

        {data.results.map((post, index) => {
          const num = String((page - 1) * 10 + index + 1).padStart(2, "0");
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

        <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />
      </main>

    </div>
  );
}

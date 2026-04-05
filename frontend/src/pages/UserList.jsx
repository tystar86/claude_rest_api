import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchUsers } from "../api/client";
import Pagination from "../components/Pagination";
import RoleBadge from "../components/RoleBadge";

export default function UserList() {
  const [data, setData] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    fetchUsers(page).then(setData).catch(() => setData({ count: 0, total_pages: 1, page, results: [] }));
  }, [page]);

  if (!data) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{data.count}</div>
        <div>
          <div className="nb-hero-label">Authors registered</div>
          <div className="nb-hero-desc">Meet the engineers writing on this platform.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">All Users</span>
        <span className="nb-section-count">Page {page} of {data.total_pages}</span>
      </div>

      {/* User rows */}
      {data.results.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No users yet.
        </div>
      )}

      {data.results.map((u, index) => {
        const num = String((page - 1) * 10 + index + 1).padStart(2, "0");
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

      <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />

    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard } from "../api/client";
import StatusBadge from "../components/StatusBadge";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function DashboardLoading() {
  const skelListRows = (count) =>
    Array.from({ length: count }, (_, j) => (
      <div key={j} className="nb-list-item nb-skel-item" aria-hidden>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="nb-skel nb-skel-title" />
          <div className="nb-skel nb-skel-meta" />
        </div>
        <div className="nb-skel nb-skel-badge" />
      </div>
    ));

  return (
    <div className="nb-layout-full" role="status" aria-live="polite" aria-busy="true">
      <div className="nb-dashboard-loading-banner">
        <div className="spinner-border" aria-hidden />
        <p className="nb-dashboard-loading-hint">
          Loading dashboard data. If the backend is waking up (typical on free hosting), this can take up to about a minute.
        </p>
      </div>

      <div style={{ borderBottom: "var(--border)", display: "grid", gridTemplateColumns: "repeat(5, 1fr)" }}>
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            style={{ borderRight: i < 4 ? "var(--border)" : "none", padding: "24px", background: "var(--white)" }}
            aria-hidden
          >
            <div className="nb-skel nb-skel-stat-value" />
            <div className="nb-skel nb-skel-stat-label" />
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderBottom: "var(--border)" }}>
        <div style={{ borderRight: "var(--border)" }}>
          <div className="nb-card-header">Latest Posts</div>
          <div className="nb-card-body">{skelListRows(6)}</div>
        </div>
        <div>
          <div className="nb-card-header">Most Commented</div>
          <div className="nb-card-body">{skelListRows(6)}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        <div style={{ borderRight: "var(--border)", borderBottom: "var(--border)" }}>
          <div className="nb-card-header">Most Used Tags</div>
          <div style={{ padding: "20px", display: "flex", flexWrap: "wrap", gap: "8px" }} aria-hidden>
            {Array.from({ length: 8 }, (_, k) => (
              <div key={k} className="nb-skel nb-skel-chip" />
            ))}
          </div>
        </div>
        <div style={{ borderBottom: "var(--border)" }}>
          <div className="nb-card-header">Top Authors</div>
          <div style={{ padding: "20px", display: "flex", flexWrap: "wrap", gap: "8px" }} aria-hidden>
            {Array.from({ length: 8 }, (_, k) => (
              <div key={k} className="nb-skel nb-skel-chip" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchDashboard().then(setData).catch(() => setData({
      stats: {},
      latest_posts: [],
      most_commented_posts: [],
      most_used_tags: [],
      top_authors: [],
    }));
  }, []);

  if (!data) {
    return <DashboardLoading />;
  }

  const stats = data.stats ?? {};

  return (
    <div className="nb-layout-full">

      {/* Stats row */}
      <div style={{ borderBottom: "var(--border)", display: "grid", gridTemplateColumns: "repeat(5, 1fr)" }}>
        {[
          { label: "Total Posts", value: stats.total_posts ?? 0, to: "/posts" },
          { label: "Comments", value: stats.comments ?? 0, to: "/comments" },
          { label: "Authors", value: stats.authors ?? 0, to: "/users" },
          { label: "Active Tags", value: stats.active_tags ?? 0, to: "/tags" },
          { label: "Avg Words", value: stats.average_depth_words ?? 0, to: null },
        ].map((s, i) => (
          <div
            key={i}
            style={{ borderRight: i < 4 ? "var(--border)" : "none", padding: "24px", background: "var(--white)" }}
          >
            {s.to ? (
              <Link to={s.to} style={{ textDecoration: "none", display: "block" }}>
                <div className="nb-stat-value">{s.value}</div>
                <div className="nb-stat-label">{s.label}</div>
              </Link>
            ) : (
              <>
                <div className="nb-stat-value">{s.value}</div>
                <div className="nb-stat-label">{s.label}</div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Content grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderBottom: "var(--border)" }}>

        {/* Latest Posts */}
        <div style={{ borderRight: "var(--border)" }}>
          <div className="nb-card-header">
            Latest Posts
          </div>
          <div className="nb-card-body">
            {data.latest_posts.length === 0 && (
              <div style={{ padding: "20px 20px", fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No posts yet.</div>
            )}
            {data.latest_posts.map((post) => (
              <div key={post.id} className="nb-list-item">
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="nb-list-title">
                    <Link to={`/posts/${post.slug}`} className="nb-list-title">{post.title}</Link>
                  </div>
                  <div className="nb-list-meta">
                    <Link to={`/users/${post.author}`} style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}>{post.author}</Link>
                    {" · "}{fmt(post.created_at)}
                  </div>
                </div>
                <StatusBadge status={post.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Most Commented */}
        <div>
          <div className="nb-card-header">
            Most Commented
          </div>
          <div className="nb-card-body">
            {data.most_commented_posts.length === 0 && (
              <div style={{ padding: "20px 20px", fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No posts yet.</div>
            )}
            {data.most_commented_posts.map((post) => (
              <div key={post.id} className="nb-list-item">
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="nb-list-title">
                    <Link to={`/posts/${post.slug}`} className="nb-list-title">{post.title}</Link>
                  </div>
                  <div className="nb-list-meta">
                    <Link to={`/users/${post.author}`} style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}>{post.author}</Link>
                    {" · "}{fmt(post.created_at)}
                  </div>
                </div>
                <span
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: "12px",
                    fontWeight: 700,
                    background: "var(--sage)",
                    border: "2px solid var(--black)",
                    padding: "2px 8px",
                    whiteSpace: "nowrap",
                    boxShadow: "2px 2px 0 var(--black)",
                  }}
                >
                  {post.comment_count ?? 0} cmts
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Tags + Authors row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>

        {/* Most Used Tags */}
        <div style={{ borderRight: "var(--border)", borderBottom: "var(--border)" }}>
          <div className="nb-card-header">Most Used Tags</div>
          <div style={{ padding: "20px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {data.most_used_tags.length === 0 && (
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No tags yet.</span>
            )}
            {data.most_used_tags.map((tag, i) => (
              <Link
                key={tag.id}
                to={`/tags/${tag.slug}`}
                className="nb-chip"
                style={i % 3 === 0 ? { background: "var(--sage)" } : i % 3 === 1 ? { background: "var(--rose)" } : {}}
              >
                {tag.name}
                <span style={{ opacity: 0.6, marginLeft: "4px" }}>({tag.post_count})</span>
              </Link>
            ))}
          </div>
        </div>

        {/* Top Authors */}
        <div style={{ borderBottom: "var(--border)" }}>
          <div className="nb-card-header">Top Authors</div>
          <div style={{ padding: "20px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {data.top_authors.length === 0 && (
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No authors yet.</span>
            )}
            {data.top_authors.map((u, idx) => (
              <Link
                key={u.id}
                to={`/users/${u.username}`}
                className="nb-chip"
                style={idx % 2 === 0 ? {} : { background: "var(--sage)" }}
              >
                <span style={{ opacity: 0.6 }}>#{idx + 1} </span>
                {u.username}
                <span style={{ opacity: 0.6, marginLeft: "4px" }}>({u.post_count})</span>
              </Link>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
}

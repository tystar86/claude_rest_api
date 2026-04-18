import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard } from "../api/client";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function DashboardLoading() {
  const statSlots = 4;
  const skelListRows = (count, withTrailSkel = true) =>
    Array.from({ length: count }, (_, j) => (
      <div key={j} className="nb-list-item nb-skel-item" aria-hidden>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="nb-skel nb-skel-title" />
          <div className="nb-skel nb-skel-meta" />
        </div>
        {withTrailSkel ? <div className="nb-skel nb-skel-badge" /> : null}
      </div>
    ));

  return (
    <div
      className="nb-layout-full nb-dashboard"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="nb-dashboard-loading-banner">
        <div className="spinner-border" aria-hidden />
        <p className="nb-dashboard-loading-hint">
          Loading dashboard data. If the backend is waking up (typical on free hosting), this can take up to about a minute.
        </p>
      </div>

      <div className="nb-dashboard-stats">
        {Array.from({ length: statSlots }, (_, i) => (
          <div key={i} className="nb-dashboard-stat-cell" aria-hidden>
            <div className="nb-skel nb-skel-stat-value" />
            <div className="nb-skel nb-skel-stat-label" />
          </div>
        ))}
      </div>

      <div className="nb-dashboard-posts-row">
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
          <div className="nb-card-header">Latest Posts</div>
          <div className="nb-card-body">{skelListRows(6, false)}</div>
        </div>
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
          <div className="nb-card-header">Most Commented</div>
          <div className="nb-card-body">{skelListRows(6)}</div>
        </div>
        <div className="nb-dashboard-panel">
          <div className="nb-card-header">Most Liked</div>
          <div className="nb-card-body">{skelListRows(6)}</div>
        </div>
      </div>

      <div className="nb-dashboard-tags-row">
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
          <div className="nb-card-header">Most Used Tags</div>
          <div className="nb-dashboard-chip-area" aria-hidden>
            {Array.from({ length: 8 }, (_, k) => (
              <div key={k} className="nb-skel nb-skel-chip" />
            ))}
          </div>
        </div>
        <div className="nb-dashboard-panel">
          <div className="nb-card-header">Most Active Authors</div>
          <div className="nb-dashboard-chip-area" aria-hidden>
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
      most_liked_posts: [],
      most_used_tags: [],
      top_authors: [],
    }));
  }, []);

  if (!data) {
    return <DashboardLoading />;
  }

  const stats = data.stats ?? {};

  const statSpecs = [
    { label: "Posts", value: stats.total_posts ?? 0 },
    { label: "Comments", value: stats.comments ?? 0 },
    { label: "Authors", value: stats.authors ?? 0 },
    { label: "Avg Words", value: stats.average_depth_words ?? 0 },
  ];

  return (
    <div className="nb-layout-full nb-dashboard">

      {/* Stats row */}
      <div className="nb-dashboard-stats">
        {statSpecs.map((s) => (
          <div key={s.label} className="nb-dashboard-stat-cell">
            <div className="nb-stat-value">{s.value}</div>
            <div className="nb-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Latest, most commented, most liked (likes = comment upvotes on the post) */}
      <div className="nb-dashboard-posts-row">

        {/* Latest Posts */}
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
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
              </div>
            ))}
          </div>
        </div>

        {/* Most Commented */}
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
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
                <span className="nb-dashboard-post-badge nb-dashboard-post-badge--comments">
                  {post.comment_count ?? 0} cmts
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Most Liked — total ▲ on approved comments */}
        <div className="nb-dashboard-panel">
          <div className="nb-card-header">
            Most Liked
          </div>
          <div className="nb-card-body">
            {(data.most_liked_posts ?? []).length === 0 && (
              <div style={{ padding: "20px 20px", fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No comment likes yet.</div>
            )}
            {(data.most_liked_posts ?? []).map((post) => (
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
                <span className="nb-dashboard-post-badge nb-dashboard-post-badge--likes">
                  ▲{post.like_count ?? 0}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Tags + Authors row */}
      <div className="nb-dashboard-tags-row">

        {/* Most Used Tags */}
        <div className="nb-dashboard-panel nb-dashboard-panel--divider-right">
          <div className="nb-card-header">Most Used Tags</div>
          <div className="nb-dashboard-chip-area">
            {data.most_used_tags.length === 0 && (
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No tags yet.</span>
            )}
            {data.most_used_tags.map((tag, i) => (
              <Link
                key={tag.id}
                to={`/tags/${tag.slug}`}
                className="nb-chip"
                style={{
                  "--chip-bg": i % 3 === 0 ? "var(--sage)" : i % 3 === 1 ? "var(--rose)" : "var(--bg)",
                }}
              >
                {tag.name}
                <span style={{ opacity: 0.6, marginLeft: "4px" }}>({tag.post_count})</span>
              </Link>
            ))}
          </div>
        </div>

        {/* Most active authors — by published post count */}
        <div className="nb-dashboard-panel">
          <div className="nb-card-header">Most Active Authors</div>
          <div className="nb-dashboard-chip-area">
            {data.top_authors.length === 0 && (
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>No authors yet.</span>
            )}
            {data.top_authors.map((u, idx) => (
              <Link
                key={u.id}
                to={`/users/${u.username}`}
                className="nb-chip"
                style={{
                  "--chip-bg": idx % 2 === 0 ? "var(--bg)" : "var(--sage)",
                }}
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

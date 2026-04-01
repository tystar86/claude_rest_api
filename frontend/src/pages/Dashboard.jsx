import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Navbar from "../components/Navbar";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function Card({
  icon,
  title,
  children,
  listLayoutClass = "d-flex flex-column gap-2",
  listStyle = { overflow: "visible" },
  cardStyle,
}) {
  return (
    <div className="insove-panel h-100 d-flex flex-column overflow-hidden" style={cardStyle}>
      <div className="d-flex justify-content-between align-items-center px-3 px-md-4 pt-3 pb-2">
        <span className="fw-semibold d-flex align-items-center gap-2" style={{ color: "#1b2b54" }}>
          <span
            className="d-inline-flex justify-content-center align-items-center"
            style={{
              width: "2rem",
              height: "2rem",
              borderRadius: "10px",
              background: "linear-gradient(145deg, #edf3ff 0%, #e7fbf6 100%)",
              color: "#2f63f5",
            }}
          >
            <i className={`bi bi-${icon}`} />
          </span>
          {title}
        </span>
      </div>
      <ul
        className={`list-unstyled m-0 px-3 px-md-4 pb-3 pb-md-4 ${listLayoutClass}`}
        style={listStyle}
      >
        {children}
      </ul>
    </div>
  );
}

function Empty({ text }) {
  return (
    <li
      className="text-center py-3"
      style={{
        color: "#6e7da2",
        borderRadius: "14px",
        background: "#f4f8ff",
      }}
    >
      {text}
    </li>
  );
}

function StatCard({ label, value, to, color = "#2f63f5", tone = "#eaf0ff" }) {
  const card = (
    <div
      className="dashboard-stat-card h-100 p-3"
      style={{ cursor: to ? "pointer" : "default" }}
    >
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <div className="fw-bold fs-3" style={{ color }}>
          {value}+
        </div>
        <div
          className="insove-pill d-inline-block"
          style={{ background: tone, color }}
        >
          {label}
        </div>
      </div>
    </div>
  );

  return (
    <div className="col-6 col-md-4 col-lg">
      {to ? (
        <Link to={to} className="text-decoration-none d-block h-100">
          {card}
        </Link>
      ) : (
        card
      )}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchDashboard().then(setData);
  }, []);

  if (!data) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" />
      </div>
    );
  }

  const stats = data.stats ?? {};

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>

      <div className="row g-2 mb-3">
        <StatCard label="Total Posts" value={stats.total_posts ?? 0} to="/posts" color="#1f4ea8" tone="#e8efff" />
        <StatCard label="Comments" value={stats.comments ?? 0} to="/comments" color="#2f8fd8" tone="#e8f6ff" />
        <StatCard label="Authors" value={stats.authors ?? 0} to="/users" color="#3b0a77" tone="#e7dbff" />
        <StatCard label="Active Tags" value={stats.active_tags ?? 0} to="/tags" color="#1f8f5f" tone="#e8f7ef" />
        <StatCard label="Average Depth (words)" value={stats.average_depth_words ?? 0} color="#275fba" tone="#e9f1ff" />
      </div>

      <div className="row g-3">

        {/* Latest Posts */}
        <div className="col-lg-6 col-12">
          <Card icon="clock-history" title="Latest Posts">
            {data.latest_posts.length === 0 && <Empty text="No posts yet." />}
            {data.latest_posts.map((post) => (
              <li
                key={post.id}
                className="dashboard-item py-2 px-3"
                style={{
                  borderRadius: "16px",
                  background: "#edf3ff",
                  border: "1px solid #d5e2ff",
                }}
              >
                <div className="d-flex justify-content-between align-items-center gap-2">
                  <div className="min-width-0">
                    <div className="text-truncate" style={{ color: "#6e7da2" }}>
                      <Link to={`/posts/${post.slug}`} className="fw-semibold text-decoration-none" style={{ color: "#173f88" }}>
                        {post.title}
                      </Link>
                      {" · "}
                      <Link to={`/users/${post.author}`} className="text-decoration-none" style={{ color: "#2a5fc7", fontWeight: 600 }}>
                        {post.author}
                      </Link>
                      {" · "}{fmt(post.created_at)}
                    </div>
                  </div>
                  <StatusBadge status={post.status} />
                </div>
              </li>
            ))}
          </Card>
        </div>

        {/* Most Commented Posts */}
        <div className="col-lg-6 col-12">
          <Card icon="chat-dots" title="Most Commented">
            {data.most_commented_posts.length === 0 && <Empty text="No posts yet." />}
            {data.most_commented_posts.map((post) => (
              <li
                key={post.id}
                className="dashboard-item py-2 px-3"
                style={{
                  borderRadius: "16px",
                  background: "#eef9ff",
                  border: "1px solid #d6ebfb",
                }}
              >
                <div className="d-flex justify-content-between align-items-center gap-2">
                  <div className="min-width-0">
                    <div className="text-truncate" style={{ color: "#6e7da2" }}>
                      <Link to={`/posts/${post.slug}`} className="fw-semibold text-decoration-none" style={{ color: "#1e5e96" }}>
                        {post.title}
                      </Link>
                      {" · "}
                      <Link to={`/users/${post.author}`} className="text-decoration-none" style={{ color: "#2f8fd8", fontWeight: 600 }}>
                        {post.author}
                      </Link>
                      {" · "}{fmt(post.created_at)}
                    </div>
                  </div>
                  <span
                    className="rounded-pill text-nowrap fw-semibold"
                    style={{
                      color: "#2f8fd8",
                      background: "#e8f6ff",
                      border: "1px solid #c9e7fa",
                      padding: "0.2rem 0.55rem",
                    }}
                  >
                    <i className="bi bi-chat me-1" />{post.comment_count ?? 0}
                  </span>
                </div>
              </li>
            ))}
          </Card>
        </div>

        {/* Most Used Tags */}
        <div className="col-12">
          <Card
            icon="tags"
            title="Most Used Tags"
            listLayoutClass="d-flex flex-row flex-wrap gap-2 gap-md-3 align-items-center"
          >
            {data.most_used_tags.length === 0 && <Empty text="No tags yet." />}
            {data.most_used_tags.map((tag) => (
              <li
                key={tag.id}
                className="dashboard-item"
              >
                <Link to={`/tags/${tag.slug}`} className="text-decoration-none">
                  <span
                    className="rounded-pill fw-semibold"
                    style={{
                      color: "#13795b",
                      background: "rgba(23, 158, 139, 0.18)",
                      border: "1px solid rgba(19, 138, 121, 0.45)",
                      padding: "0.2rem 0.6rem",
                    }}
                  >
                    <span style={{ color: "#0b4d36" }}>{tag.name}</span>
                    <span style={{ color: "#13795b" }}> ({tag.post_count} posts)</span>
                  </span>
                </Link>
              </li>
            ))}
          </Card>
        </div>

        {/* Top Authors */}
        <div className="col-12">
          <Card
            icon="trophy"
            title="Top Authors"
            listLayoutClass="d-flex flex-row flex-wrap gap-2 gap-md-3 align-items-center"
          >
            {data.top_authors.length === 0 && <Empty text="No authors yet." />}
            {data.top_authors.map((u, idx) => (
              <li
                key={u.id}
                className="dashboard-item py-1"
              >
                <Link to={`/users/${u.username}`} className="text-decoration-none">
                  <span
                    className="rounded-pill fw-semibold"
                    style={{
                      color: "#4c1d95",
                      background: "rgba(76, 29, 149, 0.14)",
                      border: "1px solid rgba(76, 29, 149, 0.42)",
                      padding: "0.2rem 0.6rem",
                    }}
                  >
                    <span style={{ color: "#4c1d95" }}>#{idx + 1} </span>
                    <span style={{ color: "#2e1065" }}>{u.username}</span>
                    <span style={{ color: "#4c1d95" }}>
                      {" "}({u.post_count} post{u.post_count !== 1 ? "s" : ""})
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </Card>
        </div>
      </div>

    </div>
  );
}

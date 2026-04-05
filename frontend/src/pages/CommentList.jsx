import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchComments } from "../api/client";
import Pagination from "../components/Pagination";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export default function CommentList() {
  const [data, setData] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1", 10);

  useEffect(() => {
    fetchComments(page).then(setData).catch(() => setData({ count: 0, total_pages: 1, page, results: [] }));
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
          <div className="nb-hero-label">Comments total</div>
          <div className="nb-hero-desc">All comments across every post on the platform.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">All Comments — Latest First</span>
        <span className="nb-section-count">Page {page} of {data.total_pages}</span>
      </div>

      {/* Comment rows */}
      {data.results.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No comments yet.
        </div>
      )}

      {data.results.map((comment, index) => {
        const num = String((page - 1) * 10 + index + 1).padStart(2, "0");
        return (
          <Link key={comment.id} to={`/posts/${comment.post_slug}`} className="nb-post-item">
            <div className="nb-post-num">{num}</div>
            <div className="nb-post-body">
              <div className="nb-post-title" style={{ fontSize: "14px" }}>
                {comment.body.length > 120 ? comment.body.slice(0, 120) + "…" : comment.body}
              </div>
              <div className="nb-post-meta">
                <span className="nb-post-meta-author">{comment.author}</span>
                <span className="nb-post-meta-sep">·</span>
                <span>{fmt(comment.created_at)}</span>
                <span className="nb-post-meta-sep">·</span>
                <span>on: {comment.post_title}</span>
              </div>
            </div>
            <div className="nb-post-right">
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", fontWeight: 700, opacity: 0.6 }}>
                ▲{comment.likes}
              </span>
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", fontWeight: 700, opacity: 0.6 }}>
                ▽{comment.dislikes}
              </span>
            </div>
          </Link>
        );
      })}

      <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />

    </div>
  );
}

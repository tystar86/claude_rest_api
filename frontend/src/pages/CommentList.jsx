import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchComments } from "../api/client";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export default function CommentList() {
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetchComments(1)
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
    fetchComments(next)
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
        Failed to load comments. Please refresh the page.
      </div>
    </div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{total}</div>
        <div>
          <div className="nb-hero-label">Comments total</div>
          <div className="nb-hero-desc">All comments across every post on the platform.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">All Comments — Latest First</span>
        <span className="nb-section-count">{items.length} loaded</span>
      </div>

      {/* Comment rows */}
      {items.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No comments yet.
        </div>
      )}

      {items.map((comment, index) => {
        const num = String(index + 1).padStart(2, "0");
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

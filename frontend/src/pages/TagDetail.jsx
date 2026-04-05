import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTag } from "../api/client";
import StatusBadge from "../components/StatusBadge";

export default function TagDetail() {
  const { slug } = useParams();
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [tagInfo, setTagInfo] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetchTag(slug, 1)
      .then((res) => {
        setNotFound(false);
        setFetchError(false);
        setItems(res.results);
        setTotal(res.count);
        setTagInfo(res.tag);
        setHasMore(res.page < res.total_pages);
        setPage(1);
      })
      .catch((err) => {
        setItems([]);
        if (err?.response?.status === 404) setNotFound(true);
        else setFetchError(true);
      });
  }, [slug]);

  const loadMore = () => {
    const next = page + 1;
    setLoadingMore(true);
    fetchTag(slug, next)
      .then((res) => {
        setItems((prev) => [...prev, ...res.results]);
        setHasMore(res.page < res.total_pages);
        setPage(next);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  if (notFound) return (
    <div className="nb-layout-full"><div className="nb-error">Tag not found.</div></div>
  );
  if (fetchError) return (
    <div className="nb-layout-full"><div className="nb-error">Failed to load tag. Please try again.</div></div>
  );
  if (items === null) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{total}</div>
        <div>
          <div className="nb-hero-label">Posts tagged</div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <span className="nb-chip nb-chip-active" style={{ fontSize: "18px", padding: "6px 16px" }}>
              {tagInfo?.name}
            </span>
          </div>
          <div className="nb-hero-desc">Browse all posts tagged with this topic.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">Posts tagged: {tagInfo?.name}</span>
        <span className="nb-section-count">{items.length} loaded</span>
      </div>

      {/* Post rows */}
      {items.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No posts with this tag yet.
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
                <span className="nb-post-meta-author">{post.author}</span>
                <span className="nb-post-meta-sep">·</span>
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

    </div>
  );
}

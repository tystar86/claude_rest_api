import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { fetchTag } from "../api/client";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";

export default function TagDetail() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    fetchTag(slug, page)
      .then((result) => { setNotFound(false); setFetchError(false); setData(result); })
      .catch((err) => {
        setData(null);
        if (err?.response?.status === 404) setNotFound(true);
        else setFetchError(true);
      });
  }, [slug, page]);

  if (notFound) return (
    <div className="nb-layout-full"><div className="nb-error">Tag not found.</div></div>
  );
  if (fetchError) return (
    <div className="nb-layout-full"><div className="nb-error">Failed to load tag. Please try again.</div></div>
  );
  if (!data) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{data.count}</div>
        <div>
          <div className="nb-hero-label">Posts tagged</div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <span className="nb-chip nb-chip-active" style={{ fontSize: "18px", padding: "6px 16px" }}>
              {data.tag.name}
            </span>
          </div>
          <div className="nb-hero-desc">Browse all posts tagged with this topic.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar">
        <span className="nb-section-title">Posts tagged: {data.tag.name}</span>
        <span className="nb-section-count">Page {page} of {data.total_pages}</span>
      </div>

      {/* Post rows */}
      {data.results.length === 0 && (
        <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
          No posts with this tag yet.
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

      <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />

    </div>
  );
}

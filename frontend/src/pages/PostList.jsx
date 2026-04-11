import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { createPost, deletePost, fetchPosts, fetchTags } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";

const TAG_VARIANT_CLASSES = ["", "t1", "t2", "t3", "t4"];

function MarkdownEditor({ value, onChange, disabled = false }) {
  const textareaRef = useRef(null);

  const insertText = (before, after = "") => {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    const selected = value.slice(start, end);
    const next = `${value.slice(0, start)}${before}${selected}${after}${value.slice(end)}`;
    onChange(next);
    requestAnimationFrame(() => {
      el.focus();
      const cursor = start + before.length + selected.length;
      el.setSelectionRange(cursor, cursor);
    });
  };

  return (
    <div>
      <div className="nb-editor-toolbar">
        <button className="nb-btn nb-btn-sm" type="button" disabled={disabled} onClick={() => insertText("`", "`")}>
          Inline code
        </button>
        <button className="nb-btn nb-btn-sm" type="button" disabled={disabled} onClick={() => insertText("```js\n", "\n```")}>
          Code block
        </button>
        <button className="nb-btn nb-btn-sm" type="button" disabled={disabled} onClick={() => insertText("## ")}>
          Heading
        </button>
        <button className="nb-btn nb-btn-sm" type="button" disabled={disabled} onClick={() => insertText("- ")}>
          Bullet
        </button>
      </div>
      <textarea
        ref={textareaRef}
        className="form-control"
        rows={5}
        placeholder="Write your post with markdown..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={{ borderTop: "none" }}
      />
    </div>
  );
}

export default function PostList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [allTags, setAllTags] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState("");
  const [form, setForm] = useState({ title: "", body: "", status: "draft", tag_ids: [] });
  const role = user?.profile?.role;
  const canManageAnyPost = role === "moderator" || role === "admin";
  const canManagePost = (post) => user && (post.author === user.username || canManageAnyPost);

  const loadAllTags = async () => {
    const firstPage = await fetchTags(1);
    let allResults = [...firstPage.results];
    if (firstPage.total_pages > 1) {
      const pageRequests = Array.from({ length: firstPage.total_pages - 1 }, (_, idx) => fetchTags(idx + 2));
      const restPages = await Promise.all(pageRequests);
      restPages.forEach((p) => { allResults = allResults.concat(p.results); });
    }
    setAllTags(allResults);
  };

  useEffect(() => {
    fetchPosts(1)
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
    loadAllTags();
  }, []);

  useEffect(() => {
    if (!location.state?.openCreate) return;
    setShowCreate(true);
    const { openCreate: _, ...restState } = location.state;
    navigate(
      { pathname: location.pathname, search: location.search },
      { replace: true, state: restState },
    );
  }, [location.pathname, location.search, location.state, navigate]);

  const loadMore = () => {
    const next = page + 1;
    setLoadingMore(true);
    fetchPosts(next)
      .then((res) => {
        setItems((prev) => [...prev, ...res.results]);
        setHasMore(res.page < res.total_pages);
        setPage(next);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  const reloadPosts = () => {
    setItems(null);
    fetchPosts(1)
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
      });
  };

  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.body.trim()) {
      setCreateError("Title and body are required.");
      return;
    }
    setCreateBusy(true);
    setCreateError("");
    try {
      const created = await createPost({ title: form.title, body: form.body, status: form.status, tag_ids: form.tag_ids });
      navigate(`/posts/${created.slug}`);
    } catch (err) {
      setCreateError(err?.response?.data?.detail || "Failed to create post.");
    } finally {
      setCreateBusy(false);
    }
  };

  const handleDeletePost = async (e, post) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete "${post.title}"?`)) return;
    try {
      await deletePost(post.slug);
      reloadPosts();
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete post.");
    }
  };

  if (items === null) return (
    <div className="nb-layout">
      <div className="nb-main nb-spinner">
        <div className="spinner-border" />
      </div>
    </div>
  );

  if (fetchError) return (
    <div className="nb-layout">
      <main className="nb-main">
        <div className="nb-error" style={{ padding: "40px 32px" }}>
          Failed to load posts. Please refresh the page.
        </div>
      </main>
    </div>
  );

  const sidebarTags = allTags.slice(0, 12);

  return (
    <div className="nb-layout">

      {/* Main column */}
      <main className="nb-main">

        {/* Hero bar */}
        <div className="nb-hero-bar">
          <div className="nb-hero-count">{total > 999 ? `${Math.floor(total / 1000)}K` : total}</div>
          <div>
            <div className="nb-hero-label">Posts published</div>
            <div className="nb-hero-desc">Technical writing from engineers worldwide. No algorithm. No ads. Just posts.</div>
          </div>
        </div>

        {/* Section bar */}
        <div className="nb-section-bar">
          <span className="nb-section-title">All Posts — Latest First</span>
          <span className="nb-section-count">{items.length} loaded</span>
        </div>

        {/* New Post toggle */}
        {user && (
          <div style={{ borderBottom: "2px solid var(--black)", padding: "10px 32px", background: "var(--bg)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              {showCreate ? "New Post Form" : "Share your knowledge"}
            </span>
            <button
              className="nb-btn nb-btn-sm"
              type="button"
              onClick={() => setShowCreate((v) => !v)}
            >
              {showCreate ? "Cancel" : "+ New Post"}
            </button>
          </div>
        )}

        {/* Create post form */}
        {user && showCreate && (
          <div style={{ borderBottom: "var(--border)", background: "var(--white)", padding: "24px 32px" }}>
            <form onSubmit={handleCreatePost}>
              <div className="nb-field">
                <label>Post Title</label>
                <input
                  className="nb-input"
                  placeholder="Enter a compelling title..."
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                  disabled={createBusy}
                />
              </div>
              <div className="nb-field">
                <label>Body</label>
                <MarkdownEditor
                  value={form.body}
                  onChange={(nextBody) => setForm((prev) => ({ ...prev, body: nextBody }))}
                  disabled={createBusy}
                />
              </div>
              {allTags.length > 0 && (
                <div className="nb-field">
                  <label>Tags</label>
                  <select
                    className="form-select"
                    multiple
                    value={form.tag_ids.map(String)}
                    onChange={(e) => {
                      const ids = Array.from(e.target.selectedOptions).map((opt) => Number(opt.value));
                      setForm((prev) => ({ ...prev, tag_ids: ids }));
                    }}
                    disabled={createBusy}
                    style={{ minHeight: "7rem" }}
                  >
                    {allTags.map((tag) => (
                      <option key={tag.id} value={tag.id}>{tag.name}</option>
                    ))}
                  </select>
                  <small style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", opacity: 0.6 }}>
                    Hold Cmd/Ctrl to select multiple tags.
                  </small>
                </div>
              )}
              <div className="nb-field">
                <label>Status</label>
                <select
                  className="form-select"
                  value={form.status}
                  onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
                  disabled={createBusy}
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                </select>
              </div>
              {createError && (
                <div className="alert alert-danger mb-3">{createError}</div>
              )}
              <button className="nb-btn" type="submit" disabled={createBusy}>
                {createBusy ? "Creating..." : "Create Post"}
              </button>
            </form>
          </div>
        )}

        {/* Post rows */}
        {items.length === 0 && (
          <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
            No posts yet.
          </div>
        )}

        {items.map((post, index) => {
          const num = String(index + 1).padStart(2, "0");
          return (
            <Link
              key={post.id}
              to={`/posts/${post.slug}`}
              className="nb-post-item"
            >
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
                <span className="nb-comment-count">{post.comment_count ?? 0} cmts</span>
                {canManagePost(post) && (
                  <button
                    className="nb-btn nb-btn-sm nb-btn-danger"
                    type="button"
                    onClick={(e) => handleDeletePost(e, post)}
                  >
                    Del
                  </button>
                )}
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

      {/* Sidebar */}
      <aside className="nb-sidebar">

        <div className="nb-sidebar-block">
          <div className="nb-sidebar-head">Platform Stats</div>
          <div className="nb-stat-row">
            <span>Total Posts</span>
            <span>{total > 999 ? `${Math.floor(total / 1000)}K+` : total}</span>
          </div>
          <div className="nb-stat-row">
            <span>Loaded</span>
            <span>{items.length}</span>
          </div>
        </div>

        {sidebarTags.length > 0 && (
          <div className="nb-sidebar-block">
            <div className="nb-sidebar-head">Browse by Tag</div>
            <div className="nb-tag-grid">
              {sidebarTags.map((tag, i) => (
                <Link
                  key={tag.id}
                  to={`/tags/${tag.slug}`}
                  className={`nb-tag-btn${TAG_VARIANT_CLASSES[i % TAG_VARIANT_CLASSES.length] ? " " + TAG_VARIANT_CLASSES[i % TAG_VARIANT_CLASSES.length] : ""}`}
                  style={i % 5 === 1 ? { background: "var(--rose)" } : i % 5 === 3 ? { background: "var(--bg-mid)" } : {}}
                >
                  {tag.name}
                </Link>
              ))}
            </div>
          </div>
        )}

        {user ? (
          <div className="nb-sidebar-cta">
            <div className="nb-cta-title">Ready to write?</div>
            <div className="nb-cta-sub">Share your knowledge with the community.</div>
            <button className="nb-cta-btn" type="button" onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Hide Form ↑" : "Write a Post →"}
            </button>
          </div>
        ) : (
          <div className="nb-sidebar-cta">
            <div className="nb-cta-title">Got something to share?</div>
            <div className="nb-cta-sub">Join engineers already writing on the platform.</div>
            <Link className="nb-cta-btn" to="/register">Create Account →</Link>
          </div>
        )}

      </aside>

    </div>
  );
}

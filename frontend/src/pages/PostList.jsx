import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { createPost, deletePost, fetchPosts, fetchTags } from "../api/client";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";

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
      <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
        <button className="btn btn-sm btn-outline-secondary" type="button" disabled={disabled} onClick={() => insertText("`", "`")}>
          Inline code
        </button>
        <button
          className="btn btn-sm btn-outline-secondary"
          type="button"
          disabled={disabled}
          onClick={() => insertText("```js\n", "\n```")}
        >
          Code block
        </button>
        <button className="btn btn-sm btn-outline-secondary" type="button" disabled={disabled} onClick={() => insertText("## ")}>
          Heading
        </button>
        <button className="btn btn-sm btn-outline-secondary" type="button" disabled={disabled} onClick={() => insertText("- ")}>
          Bullet
        </button>
      </div>
      <textarea
        ref={textareaRef}
        className="form-control insove-form-control"
        rows={5}
        placeholder="Write your post with markdown..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
    </div>
  );
}

export default function PostList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [tags, setTags] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState("");
  const [form, setForm] = useState({
    title: "",
    body: "",
    status: "draft",
    tag_ids: [],
  });
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");
  const role = user?.profile?.role;
  const canManageAnyPost = role === "moderator" || role === "admin";
  const canManagePost = (post) => user && (post.author === user.username || canManageAnyPost);

  const loadPosts = () => {
    setData(null);
    fetchPosts(page).then(setData);
  };

  const loadAllTags = async () => {
    const firstPage = await fetchTags(1);
    let allResults = [...firstPage.results];
    if (firstPage.total_pages > 1) {
      const pageRequests = Array.from(
        { length: firstPage.total_pages - 1 },
        (_, idx) => fetchTags(idx + 2)
      );
      const restPages = await Promise.all(pageRequests);
      restPages.forEach((p) => {
        allResults = allResults.concat(p.results);
      });
    }
    setTags(allResults);
  };

  useEffect(() => {
    loadPosts();
    loadAllTags();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.body.trim()) {
      setCreateError("Title and body are required.");
      return;
    }
    setCreateBusy(true);
    setCreateError("");
    try {
      const created = await createPost({
        title: form.title,
        body: form.body,
        status: form.status,
        tag_ids: form.tag_ids,
      });
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
      loadPosts();
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete post.");
    }
  };

  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="position-relative text-center mb-4">
        <span className="insove-subtle-chip">total {data.count} posts</span>
        {user && (
          <button
            className="btn nav-auth-btn nav-auth-btn-secondary btn-sm"
            type="button"
            onClick={() => setShowCreate((v) => !v)}
            style={{ position: "absolute", right: 0, top: "50%", transform: "translateY(-50%)" }}
          >
            {showCreate ? "Hide" : "New Post"}
          </button>
        )}
      </div>
      {user && showCreate && (
        <div className="insove-panel mb-3 mx-auto" style={{ maxWidth: "760px" }}>
          <div className="p-3 p-md-4">
            <form onSubmit={handleCreatePost}>
              <input
                className="form-control insove-form-control mb-2"
                placeholder="Post title"
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                disabled={createBusy}
              />
              <MarkdownEditor
                value={form.body}
                onChange={(nextBody) => setForm((prev) => ({ ...prev, body: nextBody }))}
                disabled={createBusy}
              />
              {tags.length > 0 && (
                <div className="mt-2 mb-2">
                  <label className="form-label small mb-1" style={{ color: "#173f88" }}>Tags</label>
                  <select
                    className="form-select insove-form-control"
                    multiple
                    value={form.tag_ids.map(String)}
                    onChange={(e) => {
                      const ids = Array.from(e.target.selectedOptions).map((opt) => Number(opt.value));
                      setForm((prev) => ({ ...prev, tag_ids: ids }));
                    }}
                    disabled={createBusy}
                    style={{ minHeight: "7rem" }}
                  >
                    {tags.map((tag) => (
                      <option key={tag.id} value={tag.id}>
                        {tag.name}
                      </option>
                    ))}
                  </select>
                  <small className="text-muted">Hold Cmd/Ctrl to select multiple tags.</small>
                </div>
              )}
              <select
                className="form-select insove-form-control mb-2 mt-3"
                value={form.status}
                onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
                disabled={createBusy}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </select>
              {createError && <div className="text-danger small mb-2">{createError}</div>}
              <button className="btn btn-primary" type="submit" disabled={createBusy}>
                {createBusy ? "Creating..." : "Create post"}
              </button>
            </form>
          </div>
        </div>
      )}
      <ul className="list-unstyled m-0 d-flex flex-column gap-2">
        {data.results.length === 0 && (
          <li className="text-muted py-2 text-center">No posts yet.</li>
        )}
        {data.results.map((post) => (
          <li key={post.id} className="dashboard-item">
            <Link to={`/posts/${post.slug}`} className="text-decoration-none d-block">
              <div className="insove-item px-3 py-2 w-100">
                <div className="d-flex justify-content-between align-items-center gap-2">
                  <div className="text-truncate" style={{ color: "#6e7da2" }}>
                    <span className="fw-semibold" style={{ color: "#173f88" }}>
                      {post.title}
                    </span>
                    {" · "}
                    <span style={{ color: "#2a5fc7", fontWeight: 600 }}>
                      {post.author}
                    </span>
                    {" · "}
                    {new Date(post.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <StatusBadge status={post.status} />
                    {canManagePost(post) && (
                      <button
                        className="btn btn-sm"
                        type="button"
                        onClick={(e) => handleDeletePost(e, post)}
                        style={{ border: "1px solid #f4c8d0", color: "#c72855", background: "rgba(255,255,255,0.82)" }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />
    </div>
  );
}

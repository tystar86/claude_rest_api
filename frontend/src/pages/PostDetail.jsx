import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createComment, deleteComment, deletePost, fetchPost, updateComment, updatePost, voteComment } from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import Navbar from "../components/Navbar";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

// Minimal markdown renderer: headers, code blocks, inline code, bold, lists
function renderBody(text) {
  const lines = text.split("\n");
  const elements = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <pre key={key++} className="bg-dark text-light rounded p-3 my-3" style={{ overflowX: "auto" }}>
          {lang && <div className="text-muted small mb-2">{lang}</div>}
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      i++;
      continue;
    }

    // HR
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={key++} className="my-4" />);
      i++;
      continue;
    }

    // Headers
    const h3 = line.match(/^### (.+)/);
    const h2 = line.match(/^## (.+)/);
    const h1 = line.match(/^# (.+)/);
    if (h1) { elements.push(<h2 key={key++} className="h3 fw-bold mt-4 mb-2">{h1[1]}</h2>); i++; continue; }
    if (h2) { elements.push(<h3 key={key++} className="h4 fw-semibold mt-4 mb-2">{h2[1]}</h3>); i++; continue; }
    if (h3) { elements.push(<h4 key={key++} className="h5 fw-semibold mt-3 mb-2">{h3[1]}</h4>); i++; continue; }

    // Bullet list
    if (line.match(/^[-*] /)) {
      const items = [];
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(<li key={i}>{inlineRender(lines[i].replace(/^[-*] /, ""))}</li>);
        i++;
      }
      elements.push(<ul key={key++} className="mb-3">{items}</ul>);
      continue;
    }

    // Empty line
    if (line.trim() === "") { i++; continue; }

    // Paragraph
    elements.push(<p key={key++} className="mb-3">{inlineRender(line)}</p>);
    i++;
  }
  return elements;
}

function inlineRender(text) {
  // Split on **bold** and `code`
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`"))
      return <code key={i} className="bg-light text-danger px-1 rounded">{part.slice(1, -1)}</code>;
    return part;
  });
}

function VoteButtons({ comment, onVoted }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(null);

  const vote = async (type) => {
    if (!user) return;
    setLoading(type);
    try {
      const updated = await voteComment(comment.id, type);
      onVoted(updated);
    } finally {
      setLoading(null);
    }
  };

  const isLiked = comment.user_vote === "like";
  const isDisliked = comment.user_vote === "dislike";

  return (
    <div className="d-flex align-items-center gap-2 mt-2">
      <button
        className="btn btn-sm"
        onClick={() => vote("like")}
        disabled={!user || loading !== null}
        title={user ? "Like" : "Login to vote"}
        style={
          isLiked
            ? { color: "#13795b", background: "#dff7f2", border: "1px solid #b7ece2" }
            : { color: "#13795b", background: "#f4fbf9", border: "1px solid #d0ece6" }
        }
      >
        {loading === "like"
          ? <span className="spinner-border spinner-border-sm" />
          : <><i className={`bi ${isLiked ? "bi-hand-thumbs-up-fill" : "bi-hand-thumbs-up"} me-1`} />{comment.likes}</>
        }
      </button>
      <button
        className="btn btn-sm"
        onClick={() => vote("dislike")}
        disabled={!user || loading !== null}
        title={user ? "Dislike" : "Login to vote"}
        style={
          isDisliked
            ? { color: "#b42318", background: "#fdeceb", border: "1px solid #f6c7c4" }
            : { color: "#b42318", background: "#fff6f6", border: "1px solid #f7d6d4" }
        }
      >
        {loading === "dislike"
          ? <span className="spinner-border spinner-border-sm" />
          : <><i className={`bi ${isDisliked ? "bi-hand-thumbs-down-fill" : "bi-hand-thumbs-down"} me-1`} />{comment.dislikes}</>
        }
      </button>
      {!user && <small className="text-muted">Login to vote</small>}
    </div>
  );
}

function CommentCard({ comment, onVoted, onUpdated, onDeleted, currentUsername }) {
  const canManage = currentUsername === comment.author;
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(comment.body);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleVoted = (updated) => onVoted(comment.id, updated);
  const submitEdit = async () => {
    const nextBody = draft.trim();
    if (!nextBody) {
      setError("Comment cannot be empty.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onUpdated(comment.id, nextBody);
      setIsEditing(false);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to update comment.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this comment?")) return;
    await onDeleted(comment.id);
  };

  return (
    <div className="insove-panel mb-3">
      <div className="p-3 p-md-4">
        <div className="d-flex justify-content-between align-items-start">
          <strong>
            <Link to={`/users/${comment.author}`} className="text-decoration-none text-dark">
              {comment.author}
            </Link>
          </strong>
          <div className="d-flex align-items-center gap-2">
            <small className="text-muted">{fmt(comment.created_at)}</small>
            {canManage && (
              <>
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => {
                    setIsEditing((v) => !v);
                    setDraft(comment.body);
                    setError("");
                  }}
                  style={{ border: "1px solid #d8e2ff", color: "#2f63f5", background: "rgba(255,255,255,0.82)" }}
                >
                  Edit
                </button>
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={handleDelete}
                  style={{ border: "1px solid #f4c8d0", color: "#c72855", background: "rgba(255,255,255,0.82)" }}
                >
                  Delete
                </button>
              </>
            )}
          </div>
        </div>
        {isEditing ? (
          <div className="mt-2">
            <textarea
              className="form-control insove-form-control"
              rows={3}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={saving}
            />
            {error && <div className="text-danger small mt-1">{error}</div>}
            <div className="d-flex align-items-center gap-2 mt-2">
              <button className="btn btn-sm btn-primary" type="button" disabled={saving} onClick={submitEdit}>
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                className="btn btn-sm btn-outline-secondary"
                type="button"
                disabled={saving}
                onClick={() => {
                  setIsEditing(false);
                  setDraft(comment.body);
                  setError("");
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="mb-1 mt-2" style={{ color: "#1b2b54" }}>{comment.body}</p>
        )}
        <VoteButtons comment={comment} onVoted={handleVoted} />

        {comment.replies?.length > 0 && (
          <div className="mt-3 ps-3" style={{ borderLeft: "2px solid #dbe6ff" }}>
            {comment.replies.map((reply) => (
              <div key={reply.id} className="mb-3 insove-item px-3 py-2">
                <div className="d-flex justify-content-between align-items-start">
                  <strong>
                    <Link to={`/users/${reply.author}`} className="text-decoration-none text-dark">
                      {reply.author}
                    </Link>
                  </strong>
                  <small className="text-muted">{fmt(reply.created_at)}</small>
                </div>
                <p className="mb-1 mt-2" style={{ color: "#1b2b54" }}>{reply.body}</p>
                <VoteButtons comment={reply} onVoted={(updated) => onVoted(reply.id, updated, comment.id)} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PostDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [post, setPost] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [editingPost, setEditingPost] = useState(false);
  const [postForm, setPostForm] = useState({ title: "", body: "", excerpt: "", status: "draft" });
  const [postBusy, setPostBusy] = useState(false);
  const [postError, setPostError] = useState("");
  const [newComment, setNewComment] = useState("");
  const [newCommentBusy, setNewCommentBusy] = useState(false);
  const [newCommentError, setNewCommentError] = useState("");
  const [activeJump, setActiveJump] = useState(null);
  const [scrollState, setScrollState] = useState({
    canScroll: false,
    atTop: true,
    atBottom: false,
  });

  useEffect(() => {
    fetchPost(slug).then(setPost).catch(() => setNotFound(true));
  }, [slug]);

  useEffect(() => {
    if (!post) return;
    setPostForm({
      title: post.title || "",
      body: post.body || "",
      excerpt: post.excerpt || "",
      status: post.status || "draft",
    });
  }, [post]);

  useEffect(() => {
    const updateScrollState = () => {
      const scrollTop = window.scrollY || window.pageYOffset || 0;
      const viewport = window.innerHeight || 0;
      const docHeight = document.documentElement.scrollHeight || 0;
      const canScroll = docHeight > viewport + 80;
      const atTop = scrollTop < 40;
      const atBottom = scrollTop + viewport >= docHeight - 40;
      setScrollState({ canScroll, atTop, atBottom });

      if (activeJump) {
        let stillAtTarget = false;
        if (activeJump === "top") {
          stillAtTarget = atTop;
        } else if (activeJump === "bottom") {
          stillAtTarget = atBottom;
        } else if (activeJump === "comments") {
          const section = document.getElementById("comments-section");
          if (section) {
            const targetTop = section.getBoundingClientRect().top + scrollTop;
            stillAtTarget = Math.abs(scrollTop - targetTop) <= 56;
          }
        }
        if (!stillAtTarget) setActiveJump(null);
      }
    };

    updateScrollState();
    window.addEventListener("scroll", updateScrollState, { passive: true });
    window.addEventListener("resize", updateScrollState);
    return () => {
      window.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [post, activeJump]);

  const handleVoted = (commentId, updated, parentId = null) => {
    setPost((prev) => {
      const comments = prev.comments.map((c) => {
        if (parentId) {
          // update inside replies
          if (c.id !== parentId) return c;
          return { ...c, replies: c.replies.map((r) => r.id === commentId ? updated : r) };
        }
        return c.id === commentId ? updated : c;
      });
      return { ...prev, comments };
    });
  };

  const handleCreateComment = async (e) => {
    e.preventDefault();
    const body = newComment.trim();
    if (!body) {
      setNewCommentError("Please write a comment.");
      return;
    }
    setNewCommentBusy(true);
    setNewCommentError("");
    try {
      const created = await createComment(slug, body);
      setPost((prev) => ({ ...prev, comments: [...(prev.comments || []), created] }));
      setNewComment("");
    } catch (err) {
      setNewCommentError(err?.response?.data?.detail || "Failed to create comment.");
    } finally {
      setNewCommentBusy(false);
    }
  };

  const handleUpdateComment = async (commentId, body) => {
    const updated = await updateComment(commentId, body);
    setPost((prev) => ({
      ...prev,
      comments: prev.comments.map((c) => (c.id === commentId ? updated : c)),
    }));
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await deleteComment(commentId);
      setPost((prev) => ({
        ...prev,
        comments: prev.comments.filter((c) => c.id !== commentId),
      }));
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete comment.");
    }
  };

  const role = user?.profile?.role;
  const canManagePost = user && (post?.author === user.username || role === "moderator" || role === "admin");

  const handlePostUpdate = async (e) => {
    e.preventDefault();
    if (!postForm.title.trim() || !postForm.body.trim()) {
      setPostError("Title and body are required.");
      return;
    }
    setPostBusy(true);
    setPostError("");
    try {
      const updated = await updatePost(slug, {
        title: postForm.title,
        body: postForm.body,
        excerpt: postForm.excerpt,
        status: postForm.status,
      });
      setPost(updated);
      setEditingPost(false);
      if (updated.slug && updated.slug !== slug) {
        navigate(`/posts/${updated.slug}`, { replace: true });
      }
    } catch (err) {
      setPostError(err?.response?.data?.detail || "Failed to update post.");
    } finally {
      setPostBusy(false);
    }
  };

  const handlePostDelete = async () => {
    if (!window.confirm("Delete this post?")) return;
    try {
      await deletePost(slug);
      navigate("/posts");
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete post.");
    }
  };

  if (notFound) return <div className="alert alert-danger">Post not found.</div>;
  if (!post) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="row justify-content-center">
        <div className="col-lg-8">

        <nav aria-label="breadcrumb" className="mb-3">
          <ol className="breadcrumb">
            <li className="breadcrumb-item"><Link to="/posts">Posts</Link></li>
            <li className="breadcrumb-item active">{post.title}</li>
          </ol>
        </nav>

        <div className="insove-panel mb-4">
          <div className="card-body p-4">
            {editingPost ? (
              <form onSubmit={handlePostUpdate}>
                <input
                  className="form-control insove-form-control mb-2"
                  value={postForm.title}
                  onChange={(e) => setPostForm((prev) => ({ ...prev, title: e.target.value }))}
                  disabled={postBusy}
                />
                <textarea
                  className="form-control insove-form-control mb-2"
                  rows={8}
                  value={postForm.body}
                  onChange={(e) => setPostForm((prev) => ({ ...prev, body: e.target.value }))}
                  disabled={postBusy}
                />
                <textarea
                  className="form-control insove-form-control mb-2"
                  rows={2}
                  value={postForm.excerpt}
                  onChange={(e) => setPostForm((prev) => ({ ...prev, excerpt: e.target.value }))}
                  disabled={postBusy}
                />
                <select
                  className="form-select insove-form-control mb-2"
                  value={postForm.status}
                  onChange={(e) => setPostForm((prev) => ({ ...prev, status: e.target.value }))}
                  disabled={postBusy}
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                </select>
                {postError && <div className="text-danger small mb-2">{postError}</div>}
                <div className="d-flex align-items-center gap-2">
                  <button className="btn btn-primary" type="submit" disabled={postBusy}>
                    {postBusy ? "Saving..." : "Save post"}
                  </button>
                  <button
                    className="btn btn-outline-secondary"
                    type="button"
                    onClick={() => {
                      setEditingPost(false);
                      setPostError("");
                    }}
                    disabled={postBusy}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <h1 className="h3 fw-bold mb-0">{post.title}</h1>
                  <div className="d-flex align-items-center gap-2">
                    <StatusBadge status={post.status} />
                    {canManagePost && (
                      <>
                        <button
                          className="btn btn-sm"
                          type="button"
                          onClick={() => setEditingPost(true)}
                          style={{ border: "1px solid #d8e2ff", color: "#2f63f5", background: "rgba(255,255,255,0.82)" }}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-sm"
                          type="button"
                          onClick={handlePostDelete}
                          style={{ border: "1px solid #f4c8d0", color: "#c72855", background: "rgba(255,255,255,0.82)" }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="text-muted mb-3">
                  <small>
                    by{" "}
                    <Link to={`/users/${post.author}`} className="text-decoration-none fw-medium">
                      {post.author}
                    </Link>
                    {" · "}{fmt(post.created_at)}
                  </small>
                </div>
                {post.tags.length > 0 && (
                  <div className="mb-4">
                    {post.tags.map((tag) => (
                      <Link key={tag.id} to={`/tags/${tag.slug}`} className="text-decoration-none me-1">
                        <span className="badge" style={{ color: "#13795b", background: "#dff7f2", border: "1px solid #b7ece2" }}>{tag.name}</span>
                      </Link>
                    ))}
                  </div>
                )}
                <hr />
                <div className="mt-3">{renderBody(post.body)}</div>
              </>
            )}
          </div>
        </div>

        <h5 id="comments-section" className="fw-bold mb-3">
          Comments{" "}
          <span className="text-muted fw-normal fs-6">({post.comments?.length ?? 0})</span>
        </h5>
        {user ? (
          <form className="insove-panel mb-3" onSubmit={handleCreateComment}>
            <div className="p-3 p-md-4">
              <label className="form-label fw-semibold mb-2">Add a comment</label>
              <textarea
                className="form-control insove-form-control"
                rows={3}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Write your comment..."
                disabled={newCommentBusy}
              />
              {newCommentError && <div className="text-danger small mt-2">{newCommentError}</div>}
              <div className="mt-3">
                <button className="btn btn-primary" type="submit" disabled={newCommentBusy}>
                  {newCommentBusy ? "Posting..." : "Post comment"}
                </button>
              </div>
            </div>
          </form>
        ) : (
          <p className="text-muted mb-3">Login to create, edit, or delete comments.</p>
        )}
        {post.comments?.length === 0 && <p className="text-muted">No comments yet.</p>}
        {post.comments?.map((c) => (
          <CommentCard
            key={c.id}
            comment={c}
            onVoted={handleVoted}
            onUpdated={handleUpdateComment}
            onDeleted={handleDeleteComment}
            currentUsername={user?.username}
          />
        ))}

        </div>
      </div>

      {scrollState.canScroll && (
        <div
          style={{
            position: "fixed",
            right: "1.25rem",
            bottom: "1.5rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.55rem",
            zIndex: 30,
          }}
        >
          <button
            type="button"
            className="btn nav-auth-btn nav-auth-btn-secondary btn-sm"
            aria-label="Scroll to top"
            onClick={() => {
              if (activeJump === "top") return;
              setActiveJump("top");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            aria-disabled={activeJump === "top"}
            style={{
              minWidth: "6.2rem",
              background: "rgba(237, 243, 255, 0.96)",
              boxShadow: "0 8px 18px rgba(47, 99, 245, 0.18)",
              opacity: activeJump === "top" ? 0.45 : 1,
            }}
          >
            Top
          </button>
          <button
            type="button"
            className="btn nav-auth-btn nav-auth-btn-secondary btn-sm"
            aria-label="Scroll to comments"
            onClick={() => {
              if (activeJump === "comments") return;
              setActiveJump("comments");
              const section = document.getElementById("comments-section");
              if (section) section.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            aria-disabled={activeJump === "comments"}
            style={{
              minWidth: "6.2rem",
              background: "rgba(237, 243, 255, 0.96)",
              boxShadow: "0 8px 18px rgba(47, 99, 245, 0.18)",
              opacity: activeJump === "comments" ? 0.45 : 1,
            }}
          >
            Comments
          </button>
          <button
            type="button"
            className="btn nav-auth-btn nav-auth-btn-secondary btn-sm"
            aria-label="Scroll to bottom"
            onClick={() => {
              if (activeJump === "bottom") return;
              setActiveJump("bottom");
              window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
            }}
            aria-disabled={activeJump === "bottom"}
            style={{
              minWidth: "6.2rem",
              background: "rgba(237, 243, 255, 0.96)",
              boxShadow: "0 8px 18px rgba(47, 99, 245, 0.18)",
              opacity: activeJump === "bottom" ? 0.45 : 1,
            }}
          >
            Bottom
          </button>
        </div>
      )}
    </div>
  );
}

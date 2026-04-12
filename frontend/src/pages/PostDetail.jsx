import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createComment, deleteComment, deletePost, fetchPost, fetchTags, updateComment, updatePost, voteComment } from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function renderBody(text) {
  const lines = text.split("\n");
  const elements = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <pre key={key++}>
          {lang && <div style={{ opacity: 0.5, fontSize: "11px", marginBottom: "8px", fontFamily: "'Space Mono', monospace" }}>{lang}</div>}
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      i++;
      continue;
    }

    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={key++} />);
      i++;
      continue;
    }

    const h3 = line.match(/^### (.+)/);
    const h2 = line.match(/^## (.+)/);
    const h1 = line.match(/^# (.+)/);
    if (h1) { elements.push(<h2 key={key++}>{h1[1]}</h2>); i++; continue; }
    if (h2) { elements.push(<h3 key={key++}>{h2[1]}</h3>); i++; continue; }
    if (h3) { elements.push(<h4 key={key++}>{h3[1]}</h4>); i++; continue; }

    if (line.match(/^[-*] /)) {
      const items = [];
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(<li key={i}>{inlineRender(lines[i].replace(/^[-*] /, ""))}</li>);
        i++;
      }
      elements.push(<ul key={key++}>{items}</ul>);
      continue;
    }

    if (line.trim() === "") { i++; continue; }

    elements.push(<p key={key++}>{inlineRender(line)}</p>);
    i++;
  }
  return elements;
}

function inlineRender(text) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`"))
      return <code key={i}>{part.slice(1, -1)}</code>;
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
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "10px" }}>
      <button
        className={`nb-vote-btn${isLiked ? " liked" : ""}`}
        onClick={() => vote("like")}
        disabled={!user || loading !== null}
        title={user ? "Like" : "Login to vote"}
        type="button"
      >
        {loading === "like"
          ? <span className="spinner-border spinner-border-sm" />
          : <>{isLiked ? "▲" : "△"} {comment.likes}</>
        }
      </button>
      <button
        className={`nb-vote-btn${isDisliked ? " disliked" : ""}`}
        onClick={() => vote("dislike")}
        disabled={!user || loading !== null}
        title={user ? "Dislike" : "Login to vote"}
        type="button"
      >
        {loading === "dislike"
          ? <span className="spinner-border spinner-border-sm" />
          : <>{isDisliked ? "▼" : "▽"} {comment.dislikes}</>
        }
      </button>
      {!user && (
        <small style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", opacity: 0.5 }}>
          Login to vote
        </small>
      )}
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
    if (!nextBody) { setError("Comment cannot be empty."); return; }
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
    <div className="nb-comment">
      <div className="nb-comment-header">
        <Link to={`/users/${comment.author}`} className="nb-comment-author">
          {comment.author}
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="nb-comment-date">{fmt(comment.created_at)}</span>
          {canManage && (
            <>
              <button
                className="nb-btn nb-btn-sm nb-btn-secondary"
                type="button"
                onClick={() => { setIsEditing((v) => !v); setDraft(comment.body); setError(""); }}
              >
                Edit
              </button>
              <button
                className="nb-btn nb-btn-sm nb-btn-danger"
                type="button"
                onClick={handleDelete}
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      <div className="nb-comment-body">
        {isEditing ? (
          <div>
            <textarea
              className="form-control"
              rows={3}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={saving}
            />
            {error && <div className="alert alert-danger mt-2">{error}</div>}
            <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
              <button className="nb-btn nb-btn-sm" type="button" disabled={saving} onClick={submitEdit}>
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                className="nb-btn nb-btn-sm nb-btn-secondary"
                type="button"
                disabled={saving}
                onClick={() => { setIsEditing(false); setDraft(comment.body); setError(""); }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p style={{ margin: 0, lineHeight: 1.6 }}>{comment.body}</p>
        )}
        <VoteButtons comment={comment} onVoted={handleVoted} />
      </div>

      {comment.replies?.length > 0 && (
        <div className="nb-reply-thread" style={{ padding: "12px 16px 12px 0", marginLeft: "16px", marginBottom: "12px" }}>
          {comment.replies.map((reply) => (
            <div key={reply.id} style={{ marginBottom: "12px", borderBottom: "1px solid var(--bg)", paddingBottom: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <Link to={`/users/${reply.author}`} className="nb-comment-author">{reply.author}</Link>
                <span className="nb-comment-date">{fmt(reply.created_at)}</span>
              </div>
              <p style={{ margin: 0, lineHeight: 1.6 }}>{reply.body}</p>
              <VoteButtons comment={reply} onVoted={(updated) => onVoted(reply.id, updated, comment.id)} />
            </div>
          ))}
        </div>
      )}
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
  const [postForm, setPostForm] = useState({ title: "", body: "", excerpt: "", status: "draft", tag_ids: [] });
  const [allTags, setAllTags] = useState([]);
  const [tagsError, setTagsError] = useState("");
  const [postBusy, setPostBusy] = useState(false);
  const [postError, setPostError] = useState("");
  const [newComment, setNewComment] = useState("");
  const [newCommentBusy, setNewCommentBusy] = useState(false);
  const [newCommentError, setNewCommentError] = useState("");
  const [scrollState, setScrollState] = useState({ canScroll: false, atTop: true, atBottom: false });
  const [activeJump, setActiveJump] = useState(null);

  useEffect(() => {
    fetchPost(slug).then(setPost).catch(() => setNotFound(true));
  }, [slug]);

  useEffect(() => {
    if (!editingPost || allTags.length > 0) return;
    setTagsError("");
    fetchTags(1)
      .then(async (firstPage) => {
        let results = [...firstPage.results];
        if (firstPage.total_pages > 1) {
          const rest = await Promise.all(
            Array.from({ length: firstPage.total_pages - 1 }, (_, i) => fetchTags(i + 2))
          );
          rest.forEach((p) => { results = results.concat(p.results); });
        }
        setAllTags(results);
      })
      .catch(() => setTagsError("Failed to load tags."));
  }, [editingPost, allTags.length]);

  useEffect(() => {
    if (!post) return;
    setPostForm({
      title: post.title || "",
      body: post.body || "",
      excerpt: post.excerpt || "",
      status: post.status || "draft",
      tag_ids: (post.tags || []).map((t) => t.id),
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
        if (activeJump === "top") stillAtTarget = atTop;
        else if (activeJump === "bottom") stillAtTarget = atBottom;
        else if (activeJump === "comments") {
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
    if (!body) { setNewCommentError("Please write a comment."); return; }
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
    setPost((prev) => ({ ...prev, comments: prev.comments.map((c) => (c.id === commentId ? updated : c)) }));
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await deleteComment(commentId);
      setPost((prev) => ({ ...prev, comments: prev.comments.filter((c) => c.id !== commentId) }));
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete comment.");
    }
  };

  const role = user?.profile?.role;
  const canManagePost = user && (post?.author === user.username || role === "moderator" || role === "admin");

  const handlePostUpdate = async (e) => {
    e.preventDefault();
    if (!postForm.title.trim() || !postForm.body.trim()) { setPostError("Title and body are required."); return; }
    setPostBusy(true);
    setPostError("");
    try {
      const updated = await updatePost(slug, {
        title: postForm.title,
        body: postForm.body,
        excerpt: postForm.excerpt,
        status: postForm.status,
        tag_ids: postForm.tag_ids,
      });
      setPost(updated);
      setEditingPost(false);
      if (updated.slug && updated.slug !== slug) navigate(`/posts/${updated.slug}`, { replace: true });
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

  if (notFound) return (
    <div className="nb-post-detail">
      <div className="nb-error">Post not found.</div>
    </div>
  );
  if (!post) return (
    <div className="nb-post-detail nb-spinner">
      <div className="spinner-border" />
    </div>
  );

  return (
    <div className="nb-post-detail">

      {/* Breadcrumb bar */}
      <div style={{ borderBottom: "var(--border)", padding: "10px 32px", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb mb-0">
            <li className="breadcrumb-item"><Link to="/posts">Posts</Link></li>
            <li className="breadcrumb-item active">{post.title}</li>
          </ol>
        </nav>
        {canManagePost && !editingPost && (
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="nb-btn nb-btn-sm nb-btn-secondary"
              type="button"
              onClick={() => setEditingPost(true)}
            >
              Edit
            </button>
            <button
              className="nb-btn nb-btn-sm nb-btn-danger"
              type="button"
              onClick={handlePostDelete}
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {/* Post header */}
      {!editingPost && (
        <div className="nb-post-header">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
            <h1 className="nb-post-header-title">{post.title}</h1>
            <StatusBadge status={post.status} />
          </div>
          <div style={{ marginTop: "10px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", fontWeight: 700 }}>
              by{" "}
              <Link to={`/users/${post.author}`} style={{ color: "var(--black)", textDecoration: "underline" }}>
                {post.author}
              </Link>
            </span>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.5 }}>
              {fmt(post.created_at)}
            </span>
          </div>
          {post.tags?.length > 0 && (
            <div className="nb-post-tags" style={{ marginTop: "12px" }}>
              {post.tags.map((tag) => (
                <Link key={tag.id} to={`/tags/${tag.slug}`} className="nb-tag-box">{tag.name}</Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Edit form */}
      {editingPost && (
        <div style={{ padding: "28px 32px", borderBottom: "var(--border)", background: "var(--white)" }}>
          <form onSubmit={handlePostUpdate}>
            <div className="nb-field">
              <label>Title</label>
              <input
                className="nb-input"
                value={postForm.title}
                onChange={(e) => setPostForm((prev) => ({ ...prev, title: e.target.value }))}
                disabled={postBusy}
              />
            </div>
            <div className="nb-field">
              <label>Body</label>
              <textarea
                className="form-control"
                rows={8}
                value={postForm.body}
                onChange={(e) => setPostForm((prev) => ({ ...prev, body: e.target.value }))}
                disabled={postBusy}
              />
            </div>
            <div className="nb-field">
              <label>Excerpt</label>
              <textarea
                className="form-control"
                rows={2}
                value={postForm.excerpt}
                onChange={(e) => setPostForm((prev) => ({ ...prev, excerpt: e.target.value }))}
                disabled={postBusy}
              />
            </div>
            {tagsError && <div className="alert alert-danger mb-3">{tagsError}</div>}
            {allTags.length > 0 && (
              <div className="nb-field">
                <label>Tags</label>
                <select
                  className="form-select"
                  multiple
                  value={postForm.tag_ids.map(String)}
                  onChange={(e) => {
                    const ids = Array.from(e.target.selectedOptions).map((opt) => Number(opt.value));
                    setPostForm((prev) => ({ ...prev, tag_ids: ids }));
                  }}
                  disabled={postBusy}
                  style={{ minHeight: "7rem" }}
                >
                  {allTags.map((tag) => (
                    <option key={tag.id} value={tag.id}>{tag.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="nb-field">
              <label>Status</label>
              <select
                className="form-select"
                value={postForm.status}
                onChange={(e) => setPostForm((prev) => ({ ...prev, status: e.target.value }))}
                disabled={postBusy}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </select>
            </div>
            {postError && <div className="alert alert-danger mb-3">{postError}</div>}
            <div style={{ display: "flex", gap: "8px" }}>
              <button className="nb-btn" type="submit" disabled={postBusy}>
                {postBusy ? "Saving..." : "Save Post"}
              </button>
              <button
                className="nb-btn nb-btn-secondary"
                type="button"
                onClick={() => { setEditingPost(false); setPostError(""); }}
                disabled={postBusy}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Post body */}
      {!editingPost && (
        <div className="nb-post-content">
          {renderBody(post.body)}
        </div>
      )}

      {/* Comments section */}
      <div style={{ borderTop: "var(--border)" }}>
        <div className="nb-section-bar" id="comments-section">
          <span className="nb-section-title">
            Comments ({post.comments?.length ?? 0})
          </span>
        </div>

        <div style={{ padding: "24px 32px", background: "var(--bg)" }}>
          {user ? (
            <form onSubmit={handleCreateComment} style={{ marginBottom: "24px" }}>
              <div className="nb-field">
                <label>Add a Comment</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Write your comment..."
                  disabled={newCommentBusy}
                />
              </div>
              {newCommentError && <div className="alert alert-danger mb-3">{newCommentError}</div>}
              <button className="nb-btn" type="submit" disabled={newCommentBusy}>
                {newCommentBusy ? "Posting..." : "Post Comment"}
              </button>
            </form>
          ) : (
            <div style={{ marginBottom: "24px", fontFamily: "'Space Mono', monospace", fontSize: "12px", opacity: 0.6 }}>
              <Link to="/login" style={{ color: "var(--black)", fontWeight: 700 }}>Login</Link> to post a comment.
            </div>
          )}

          {post.comments?.length === 0 && (
            <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", opacity: 0.5 }}>No comments yet.</div>
          )}

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

      {/* Scroll helper buttons */}
      {scrollState.canScroll && (
        <div className="nb-scroll-btns">
          <button
            type="button"
            className="nb-btn nb-btn-sm nb-btn-secondary"
            aria-label="Scroll to top"
            onClick={() => { if (activeJump === "top") return; setActiveJump("top"); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            style={{ opacity: activeJump === "top" ? 0.45 : 1 }}
          >
            Top
          </button>
          <button
            type="button"
            className="nb-btn nb-btn-sm nb-btn-secondary"
            aria-label="Scroll to comments"
            onClick={() => {
              if (activeJump === "comments") return;
              setActiveJump("comments");
              const section = document.getElementById("comments-section");
              if (section) section.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            style={{ opacity: activeJump === "comments" ? 0.45 : 1 }}
          >
            Comments
          </button>
          <button
            type="button"
            className="nb-btn nb-btn-sm nb-btn-secondary"
            aria-label="Scroll to bottom"
            onClick={() => { if (activeJump === "bottom") return; setActiveJump("bottom"); window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" }); }}
            style={{ opacity: activeJump === "bottom" ? 0.45 : 1 }}
          >
            Bottom
          </button>
        </div>
      )}

    </div>
  );
}

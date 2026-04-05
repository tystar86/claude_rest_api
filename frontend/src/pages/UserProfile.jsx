import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import RoleBadge from "../components/RoleBadge";
import StatusBadge from "../components/StatusBadge";
import { updateProfile, fetchUser, fetchUserComments } from "../api/client";

export default function UserProfile() {
  const { user, setUser, loading } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = searchParams.get("tab") || "settings";

  const [usernameVal, setUsernameVal] = useState("");
  const [usernameError, setUsernameError] = useState("");
  const [usernameSuccess, setUsernameSuccess] = useState("");
  const [savingUsername, setSavingUsername] = useState(false);

  const [pwCurrent, setPwCurrent] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwConfirm, setPwConfirm] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  // Posts tab state — null means "not yet loaded / loading"
  const [postItems, setPostItems] = useState(null);
  const [postsTotal, setPostsTotal] = useState(0);
  const [postsPage, setPostsPage] = useState(1);
  const [postsHasMore, setPostsHasMore] = useState(false);
  const [postsLoadingMore, setPostsLoadingMore] = useState(false);

  // Comments tab state — null means "not yet loaded / loading"
  const [commentItems, setCommentItems] = useState(null);
  const [commentsTotal, setCommentsTotal] = useState(0);
  const [commentsPage, setCommentsPage] = useState(1);
  const [commentsHasMore, setCommentsHasMore] = useState(false);
  const [commentsLoadingMore, setCommentsLoadingMore] = useState(false);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [loading, user, navigate]);

  useEffect(() => {
    if (!user) return;
    if (tab === "posts") {
      setPostItems(null);
      fetchUser(user.username, 1)
        .then((res) => {
          setPostItems(res.results);
          setPostsTotal(res.count);
          setPostsHasMore(res.page < res.total_pages);
          setPostsPage(1);
        })
        .catch(() => {
          setPostItems([]);
          setPostsTotal(0);
          setPostsHasMore(false);
        });
    } else if (tab === "comments") {
      setCommentItems(null);
      fetchUserComments(user.username, 1)
        .then((res) => {
          setCommentItems(res.results);
          setCommentsTotal(res.count);
          setCommentsHasMore(res.page < res.total_pages);
          setCommentsPage(1);
        })
        .catch(() => {
          setCommentItems([]);
          setCommentsTotal(0);
          setCommentsHasMore(false);
        });
    }
  }, [user, tab]);

  const loadMorePosts = () => {
    const next = postsPage + 1;
    setPostsLoadingMore(true);
    fetchUser(user.username, next)
      .then((res) => {
        setPostItems((prev) => [...prev, ...res.results]);
        setPostsHasMore(res.page < res.total_pages);
        setPostsPage(next);
      })
      .catch(() => {})
      .finally(() => setPostsLoadingMore(false));
  };

  const loadMoreComments = () => {
    const next = commentsPage + 1;
    setCommentsLoadingMore(true);
    fetchUserComments(user.username, next)
      .then((res) => {
        setCommentItems((prev) => [...prev, ...res.results]);
        setCommentsHasMore(res.page < res.total_pages);
        setCommentsPage(next);
      })
      .catch(() => {})
      .finally(() => setCommentsLoadingMore(false));
  };

  if (loading) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );
  if (!user) return null;

  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setUsernameError(""); setUsernameSuccess(""); setSavingUsername(true);
    try {
      const updated = await updateProfile({ username: usernameVal.trim() });
      setUser(updated); setUsernameVal(""); setUsernameSuccess("Username updated successfully!");
    } catch (err) {
      const d = err.response?.data;
      setUsernameError(d?.username || d?.detail || "Failed to update username.");
    } finally { setSavingUsername(false); }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPwError(""); setPwSuccess("");
    if (pwNew !== pwConfirm) { setPwError("New passwords do not match."); return; }
    setSavingPw(true);
    try {
      const updated = await updateProfile({ current_password: pwCurrent, new_password: pwNew });
      setUser(updated); setPwCurrent(""); setPwNew(""); setPwConfirm("");
      setPwSuccess("Password updated successfully!");
    } catch (err) {
      const d = err.response?.data;
      setPwError(d?.current_password || d?.new_password || d?.detail || "Failed to update password.");
    } finally { setSavingPw(false); }
  };

  const TABS = [
    { key: "settings", label: "Settings" },
    { key: "posts", label: "My Posts" },
    { key: "comments", label: "My Comments" },
  ];

  return (
    <div className="nb-layout" style={{ gridTemplateColumns: "280px 1fr" }}>

      {/* Sidebar */}
      <aside className="nb-sidebar" style={{ borderRight: "var(--border)" }}>
        <div className="nb-sidebar-block" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "60px", lineHeight: 1, marginBottom: "12px" }}>
            <i className="bi bi-person-square" style={{ color: "var(--black)" }} />
          </div>
          <div className="nb-username">{user.username}</div>
          <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "11px", opacity: 0.55, marginBottom: "10px" }}>
            {user.email}
          </div>
          <div>
            <RoleBadge role={user.profile?.role} />
            {(!user.profile?.role || user.profile?.role === "user") && (
              <span className="nb-status-draft">User</span>
            )}
          </div>
          {user.profile?.bio && (
            <div style={{ fontSize: "13px", opacity: 0.7, marginTop: "12px", lineHeight: 1.5 }}>
              {user.profile.bio}
            </div>
          )}
        </div>

        <div className="nb-sidebar-block">
          <div className="nb-sidebar-head">Account</div>
          <div className="nb-stat-row">
            <span>Joined</span>
            <span style={{ fontSize: "12px" }}>
              {new Date(user.date_joined).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
            </span>
          </div>
          <div className="nb-stat-row">
            <span>Role</span>
            <span>{user.profile?.role ?? "user"}</span>
          </div>
        </div>

        {/* Tab nav as sidebar list */}
        <div style={{ borderBottom: "var(--border)" }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setSearchParams({ tab: t.key })}
              style={{
                display: "block",
                width: "100%",
                border: "none",
                borderBottom: "2px solid var(--black)",
                padding: "12px 24px",
                background: tab === t.key ? "var(--black)" : "var(--white)",
                color: tab === t.key ? "var(--sage)" : "var(--black)",
                fontFamily: "'Space Mono', monospace",
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                textAlign: "left",
                cursor: "pointer",
                transition: "background 0.1s",
              }}
            >
              {tab === t.key ? "▸ " : "  "}{t.label}
            </button>
          ))}
        </div>
      </aside>

      {/* Main content */}
      <main className="nb-main">

        {/* ── Settings ── */}
        {tab === "settings" && (
          <>
            <div className="nb-section-bar">
              <span className="nb-section-title">Account Settings</span>
            </div>
            <div style={{ padding: "32px", background: "var(--bg)" }}>

              {/* Change Username */}
              <div className="nb-panel" style={{ marginBottom: "24px" }}>
                <div className="nb-panel-header">Change Username</div>
                <div style={{ padding: "24px" }}>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", marginBottom: "16px", opacity: 0.6 }}>
                    Current: <strong style={{ opacity: 1 }}>{user.username}</strong>
                  </div>
                  <form onSubmit={handleUsernameSubmit}>
                    <div className="nb-field">
                      <label>New Username</label>
                      <input
                        type="text"
                        className="nb-input"
                        placeholder="Enter new username"
                        value={usernameVal}
                        onChange={(e) => setUsernameVal(e.target.value)}
                        required
                        minLength={3}
                      />
                    </div>
                    {usernameError && <div className="alert alert-danger mb-3">{usernameError}</div>}
                    {usernameSuccess && <div className="alert alert-success mb-3">{usernameSuccess}</div>}
                    <button type="submit" className="nb-btn" disabled={savingUsername}>
                      {savingUsername && <span className="spinner-border spinner-border-sm me-2" />}
                      Save Username
                    </button>
                  </form>
                </div>
              </div>

              {/* Change Password */}
              <div className="nb-panel">
                <div className="nb-panel-header">Change Password</div>
                <div style={{ padding: "24px" }}>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "12px", marginBottom: "16px", opacity: 0.6 }}>
                    Choose a strong password with at least 8 characters.
                  </div>
                  <form onSubmit={handlePasswordSubmit}>
                    <div className="nb-field">
                      <label>Current Password</label>
                      <input type="password" className="nb-input" placeholder="Enter current password" value={pwCurrent} onChange={(e) => setPwCurrent(e.target.value)} required />
                    </div>
                    <div className="nb-field">
                      <label>New Password</label>
                      <input type="password" className="nb-input" placeholder="At least 8 characters" value={pwNew} onChange={(e) => setPwNew(e.target.value)} required minLength={8} />
                    </div>
                    <div className="nb-field">
                      <label>Confirm New Password</label>
                      <input type="password" className="nb-input" placeholder="Repeat new password" value={pwConfirm} onChange={(e) => setPwConfirm(e.target.value)} required />
                    </div>
                    {pwError && <div className="alert alert-danger mb-3">{pwError}</div>}
                    {pwSuccess && <div className="alert alert-success mb-3">{pwSuccess}</div>}
                    <button type="submit" className="nb-btn" disabled={savingPw}>
                      {savingPw && <span className="spinner-border spinner-border-sm me-2" />}
                      Save Password
                    </button>
                  </form>
                </div>
              </div>

            </div>
          </>
        )}

        {/* ── My Posts ── */}
        {tab === "posts" && (
          <>
            <div className="nb-section-bar">
              <span className="nb-section-title">My Posts</span>
              {postsTotal > 0 && <span className="nb-section-count">{postsTotal} total</span>}
            </div>

            {postItems === null && (
              <div className="nb-spinner"><div className="spinner-border" /></div>
            )}

            {postItems !== null && (
              <>
                {postItems.length === 0 && (
                  <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
                    You haven&apos;t written any posts yet.
                  </div>
                )}

                {postItems.map((post, index) => {
                  const num = String(index + 1).padStart(2, "0");
                  return (
                    <Link key={post.id} to={`/posts/${post.slug}`} className="nb-post-item">
                      <div className="nb-post-num">{num}</div>
                      <div className="nb-post-body">
                        <div className="nb-post-title">{post.title}</div>
                        <div className="nb-post-meta">
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

                {postsHasMore && (
                  <button
                    className="nb-btn nb-btn-full"
                    onClick={loadMorePosts}
                    disabled={postsLoadingMore}
                    style={{ marginTop: "16px" }}
                  >
                    {postsLoadingMore ? "Loading…" : "Load More"}
                  </button>
                )}
              </>
            )}
          </>
        )}

        {/* ── My Comments ── */}
        {tab === "comments" && (
          <>
            <div className="nb-section-bar">
              <span className="nb-section-title">My Comments</span>
              {commentsTotal > 0 && <span className="nb-section-count">{commentsTotal} total</span>}
            </div>

            {commentItems === null && (
              <div className="nb-spinner"><div className="spinner-border" /></div>
            )}

            {commentItems !== null && (
              <>
                {commentItems.length === 0 && (
                  <div style={{ padding: "40px 32px", textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>
                    You haven&apos;t commented on any posts yet.
                  </div>
                )}

                {commentItems.map((comment, index) => {
                  const num = String(index + 1).padStart(2, "0");
                  return (
                    <Link key={comment.id} to={`/posts/${comment.post_slug}`} className="nb-post-item">
                      <div className="nb-post-num">{num}</div>
                      <div className="nb-post-body">
                        <div className="nb-post-title" style={{ fontSize: "14px" }}>
                          {comment.body.length > 100 ? comment.body.slice(0, 100) + "…" : comment.body}
                        </div>
                        <div className="nb-post-meta">
                          <span>on: {comment.post_title}</span>
                          <span className="nb-post-meta-sep">·</span>
                          <span>
                            {new Date(comment.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                          </span>
                        </div>
                      </div>
                      <div className="nb-post-right">
                        {comment.likes > 0 && (
                          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", fontWeight: 700, opacity: 0.6 }}>
                            ▲{comment.likes}
                          </span>
                        )}
                        {comment.dislikes > 0 && (
                          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", fontWeight: 700, opacity: 0.6 }}>
                            ▽{comment.dislikes}
                          </span>
                        )}
                      </div>
                    </Link>
                  );
                })}

                {commentsHasMore && (
                  <button
                    className="nb-btn nb-btn-full"
                    onClick={loadMoreComments}
                    disabled={commentsLoadingMore}
                    style={{ marginTop: "16px" }}
                  >
                    {commentsLoadingMore ? "Loading…" : "Load More"}
                  </button>
                )}
              </>
            )}
          </>
        )}

      </main>

    </div>
  );
}

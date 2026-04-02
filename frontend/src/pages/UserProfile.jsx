import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/Navbar";
import Pagination from "../components/Pagination";
import RoleBadge from "../components/RoleBadge";
import StatusBadge from "../components/StatusBadge";
import { updateProfile, fetchUser, fetchUserComments } from "../api/client";

export default function UserProfile() {
  const { user, setUser, loading } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = searchParams.get("tab") || "settings";
  const page = parseInt(searchParams.get("page") || "1");

  // Settings – username form
  const [usernameVal, setUsernameVal] = useState("");
  const [usernameError, setUsernameError] = useState("");
  const [usernameSuccess, setUsernameSuccess] = useState("");
  const [savingUsername, setSavingUsername] = useState(false);

  // Settings – password form
  const [pwCurrent, setPwCurrent] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwConfirm, setPwConfirm] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  // My Posts / My Comments data
  const [postsData, setPostsData] = useState(null);
  const [commentsData, setCommentsData] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [loading, user, navigate]);

  // Load data when switching to posts or comments tab
  useEffect(() => {
    if (!user) return;
    if (tab === "posts") {
      setLoadingContent(true);
      fetchUser(user.username, page)
        .then(setPostsData)
        .catch(() => setPostsData(null))
        .finally(() => setLoadingContent(false));
    } else if (tab === "comments") {
      setLoadingContent(true);
      fetchUserComments(user.username, page)
        .then(setCommentsData)
        .catch(() => setCommentsData(null))
        .finally(() => setLoadingContent(false));
    }
  }, [user, tab, page]);

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border" />
      </div>
    );
  }
  if (!user) return null;

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setUsernameError("");
    setUsernameSuccess("");
    setSavingUsername(true);
    try {
      const updated = await updateProfile({ username: usernameVal.trim() });
      setUser(updated);
      setUsernameVal("");
      setUsernameSuccess("Username updated successfully!");
    } catch (err) {
      const data = err.response?.data;
      setUsernameError(data?.username || data?.detail || "Failed to update username.");
    } finally {
      setSavingUsername(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");
    if (pwNew !== pwConfirm) {
      setPwError("New passwords do not match.");
      return;
    }
    setSavingPw(true);
    try {
      const updated = await updateProfile({ current_password: pwCurrent, new_password: pwNew });
      setUser(updated);
      setPwCurrent("");
      setPwNew("");
      setPwConfirm("");
      setPwSuccess("Password updated successfully!");
    } catch (err) {
      const data = err.response?.data;
      setPwError(
        data?.current_password || data?.new_password || data?.detail || "Failed to update password."
      );
    } finally {
      setSavingPw(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>

      <div className="row g-4">
        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <div className="col-md-3">
          <div className="insove-panel text-center p-4">
            <i className="bi bi-person-circle text-secondary" style={{ fontSize: "4rem" }} />
            <h5 className="fw-bold mt-2 mb-0">{user.username}</h5>
            <small className="text-muted d-block">{user.email}</small>
            <div className="mt-2">
              <RoleBadge role={user.profile?.role} />
              {user.profile?.role === "user" && (
                <span className="badge bg-secondary">User</span>
              )}
            </div>
            {user.profile?.bio && (
              <p className="text-muted small mt-3 mb-0">{user.profile.bio}</p>
            )}
            <hr />
            <small className="text-muted">
              Joined{" "}
              {new Date(user.date_joined).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </small>
          </div>
        </div>

        {/* ── Main Content ─────────────────────────────────────────────────── */}
        <div className="col-md-9">
          {/* Tab nav */}
          <ul className="nav nav-tabs mb-4">
            <li className="nav-item">
              <button
                className={`nav-link${tab === "settings" ? " active fw-semibold" : ""}`}
                onClick={() => setSearchParams({ tab: "settings" })}
              >
                <i className="bi bi-gear me-1" />
                Settings
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link${tab === "posts" ? " active fw-semibold" : ""}`}
                onClick={() => setSearchParams({ tab: "posts", page: "1" })}
              >
                <i className="bi bi-file-text me-1" />
                My Posts
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link${tab === "comments" ? " active fw-semibold" : ""}`}
                onClick={() => setSearchParams({ tab: "comments", page: "1" })}
              >
                <i className="bi bi-chat-left-text me-1" />
                My Comments
              </button>
            </li>
          </ul>

          {/* ── Settings ───────────────────────────────────────────────────── */}
          {tab === "settings" && (
            <div className="row g-4">
              {/* Change Username */}
              <div className="col-12">
                <div className="insove-panel p-4">
                  <h6 className="fw-bold mb-1">
                    <i className="bi bi-person me-2 text-primary" />
                    Change Username
                  </h6>
                  <p className="text-muted small mb-3">
                    Current username:{" "}
                    <strong className="text-dark">{user.username}</strong>
                  </p>
                  <form onSubmit={handleUsernameSubmit}>
                    <div className="mb-3">
                      <label className="form-label small fw-semibold">New Username</label>
                      <input
                        type="text"
                        className="form-control insove-form-control"
                        placeholder="Enter new username"
                        value={usernameVal}
                        onChange={(e) => setUsernameVal(e.target.value)}
                        required
                        minLength={3}
                      />
                    </div>
                    {usernameError && (
                      <div className="alert alert-danger py-2 small">{usernameError}</div>
                    )}
                    {usernameSuccess && (
                      <div className="alert alert-success py-2 small">{usernameSuccess}</div>
                    )}
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm px-4"
                      disabled={savingUsername}
                    >
                      {savingUsername && (
                        <span className="spinner-border spinner-border-sm me-2" />
                      )}
                      Save Username
                    </button>
                  </form>
                </div>
              </div>

              {/* Change Password */}
              <div className="col-12">
                <div className="insove-panel p-4">
                  <h6 className="fw-bold mb-1">
                    <i className="bi bi-lock me-2 text-primary" />
                    Change Password
                  </h6>
                  <p className="text-muted small mb-3">
                    Choose a strong password with at least 8 characters.
                  </p>
                  <form onSubmit={handlePasswordSubmit}>
                    <div className="mb-3">
                      <label className="form-label small fw-semibold">Current Password</label>
                      <input
                        type="password"
                        className="form-control insove-form-control"
                        placeholder="Enter current password"
                        value={pwCurrent}
                        onChange={(e) => setPwCurrent(e.target.value)}
                        required
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small fw-semibold">New Password</label>
                      <input
                        type="password"
                        className="form-control insove-form-control"
                        placeholder="At least 8 characters"
                        value={pwNew}
                        onChange={(e) => setPwNew(e.target.value)}
                        required
                        minLength={8}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small fw-semibold">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        className="form-control insove-form-control"
                        placeholder="Repeat new password"
                        value={pwConfirm}
                        onChange={(e) => setPwConfirm(e.target.value)}
                        required
                      />
                    </div>
                    {pwError && (
                      <div className="alert alert-danger py-2 small">{pwError}</div>
                    )}
                    {pwSuccess && (
                      <div className="alert alert-success py-2 small">{pwSuccess}</div>
                    )}
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm px-4"
                      disabled={savingPw}
                    >
                      {savingPw && (
                        <span className="spinner-border spinner-border-sm me-2" />
                      )}
                      Save Password
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* ── My Posts ───────────────────────────────────────────────────── */}
          {tab === "posts" && (
            <div>
              {loadingContent ? (
                <div className="text-center py-5">
                  <div className="spinner-border" />
                </div>
              ) : postsData && (
                <div>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="insove-title mb-0">My Posts</h5>
                    <span className="insove-subtle-chip">{postsData.count} total</span>
                  </div>
                  <div className="insove-panel">
                    <ul className="list-group list-group-flush">
                      {postsData.results.length === 0 && (
                        <li className="list-group-item text-muted py-4 text-center">
                          You haven't written any posts yet.
                        </li>
                      )}
                      {postsData.results.map((post) => (
                        <li key={post.id} className="list-group-item py-3">
                          <div className="d-flex justify-content-between align-items-start">
                            <div>
                              <h6 className="mb-1 fw-semibold">
                                <Link
                                  to={`/posts/${post.slug}`}
                                  className="text-decoration-none"
                                  style={{ color: "#173f88" }}
                                >
                                  {post.title}
                                </Link>
                              </h6>
                              <small className="text-muted">
                                {new Date(post.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  year: "numeric",
                                })}
                              </small>
                              {post.tags.length > 0 && (
                                <div className="mt-1">
                                  {post.tags.map((tag) => (
                                    <Link
                                      key={tag.id}
                                      to={`/tags/${tag.slug}`}
                                      className="text-decoration-none me-1"
                                    >
                                      <span
                                        className="badge"
                                        style={{
                                          color: "#13795b",
                                          background: "#dff7f2",
                                          border: "1px solid #b7ece2",
                                        }}
                                      >
                                        {tag.name}
                                      </span>
                                    </Link>
                                  ))}
                                </div>
                              )}
                            </div>
                            <StatusBadge status={post.status} />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <Pagination
                    page={page}
                    totalPages={postsData.total_pages}
                    onChange={(p) => setSearchParams({ tab: "posts", page: p })}
                  />
                </div>
              )}
            </div>
          )}

          {/* ── My Comments ────────────────────────────────────────────────── */}
          {tab === "comments" && (
            <div>
              {loadingContent ? (
                <div className="text-center py-5">
                  <div className="spinner-border" />
                </div>
              ) : commentsData && (
                <div>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="insove-title mb-0">My Comments</h5>
                    <span className="insove-subtle-chip">{commentsData.count} total</span>
                  </div>
                  <div className="insove-panel">
                    <ul className="list-group list-group-flush">
                      {commentsData.results.length === 0 && (
                        <li className="list-group-item text-muted py-4 text-center">
                          You haven't commented on any posts yet.
                        </li>
                      )}
                      {commentsData.results.map((comment) => (
                        <li key={comment.id} className="list-group-item py-3">
                          <div className="mb-1">
                            <Link
                              to={`/posts/${comment.post_slug}`}
                              className="text-decoration-none fw-semibold small"
                              style={{ color: "#173f88" }}
                            >
                              <i className="bi bi-file-text me-1" />
                              {comment.post_title}
                            </Link>
                          </div>
                          <p
                            className="mb-1 text-muted small"
                            style={{
                              display: "-webkit-box",
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: "vertical",
                              overflow: "hidden",
                            }}
                          >
                            {comment.body}
                          </p>
                          <div className="d-flex align-items-center gap-3 mt-1">
                            <small className="text-muted">
                              <i className="bi bi-calendar3 me-1" />
                              {new Date(comment.created_at).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </small>
                            {comment.likes > 0 && (
                              <small className="text-muted">
                                <i className="bi bi-hand-thumbs-up me-1" />
                                {comment.likes}
                              </small>
                            )}
                            {comment.dislikes > 0 && (
                              <small className="text-muted">
                                <i className="bi bi-hand-thumbs-down me-1" />
                                {comment.dislikes}
                              </small>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <Pagination
                    page={page}
                    totalPages={commentsData.total_pages}
                    onChange={(p) => setSearchParams({ tab: "comments", page: p })}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

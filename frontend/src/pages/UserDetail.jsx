import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { fetchUser } from "../api/client";
import Pagination from "../components/Pagination";
import RoleBadge from "../components/RoleBadge";
import StatusBadge from "../components/StatusBadge";
import Navbar from "../components/Navbar";

export default function UserDetail() {
  const { username } = useParams();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    setData(null);
    setNotFound(false);
    setFetchError(false);
    fetchUser(username, page)
      .then(setData)
      .catch((err) => {
        if (err?.response?.status === 404) setNotFound(true);
        else setFetchError(true);
      });
  }, [username, page]);

  if (notFound) return <div className="alert alert-danger">User not found.</div>;
  if (fetchError) return <div className="alert alert-warning">Failed to load user. Please try again.</div>;
  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  const { user } = data;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <nav aria-label="breadcrumb" className="mb-3">
        <ol className="breadcrumb">
          <li className="breadcrumb-item"><Link to="/users">Users</Link></li>
          <li className="breadcrumb-item active">{user.username}</li>
        </ol>
      </nav>

      <div className="row g-4">
        <div className="col-md-3">
          <div className="insove-panel text-center p-4">
            <i className="bi bi-person-circle text-secondary" style={{ fontSize: "4rem" }} />
            <h5 className="fw-bold mt-2 mb-0">{user.username}</h5>
            <small className="text-muted">{user.email}</small>
            <div className="mt-2">
              <RoleBadge role={user.profile?.role} />
              {user.profile?.role === "user" && <span className="badge bg-secondary">User</span>}
            </div>
            {user.profile?.bio && <p className="text-muted small mt-3 mb-0">{user.profile.bio}</p>}
            <hr />
            <small className="text-muted">
              Joined {new Date(user.date_joined).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
            </small>
          </div>
        </div>

        <div className="col-md-9">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="insove-title mb-0">Posts</h5>
            <span className="insove-subtle-chip">{data.count} total</span>
          </div>
          <div className="insove-panel">
            <ul className="list-group list-group-flush">
              {data.results.length === 0 && (
                <li className="list-group-item text-muted py-4 text-center">No posts yet.</li>
              )}
              {data.results.map((post) => (
                <li key={post.id} className="list-group-item py-3">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <h6 className="mb-1 fw-semibold">
                        <Link to={`/posts/${post.slug}`} className="text-decoration-none" style={{ color: "#173f88" }}>{post.title}</Link>
                      </h6>
                      <small className="text-muted">
                        {new Date(post.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </small>
                      {post.tags.length > 0 && (
                        <div className="mt-1">
                          {post.tags.map((tag) => (
                            <Link key={tag.id} to={`/tags/${tag.slug}`} className="text-decoration-none me-1">
                              <span className="badge" style={{ color: "#13795b", background: "#dff7f2", border: "1px solid #b7ece2" }}>{tag.name}</span>
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
          <Pagination page={page} totalPages={data.total_pages} onChange={(p) => setSearchParams({ page: p })} />
        </div>
      </div>
    </div>
  );
}

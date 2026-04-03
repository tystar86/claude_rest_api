import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchUsers } from "../api/client";
import Pagination from "../components/Pagination";
import RoleBadge from "../components/RoleBadge";
import Navbar from "../components/Navbar";

export default function UserList() {
  const [data, setData] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    setData(null);
    fetchUsers(page).then(setData).catch(() => setData({ count: 0, total_pages: 1, page, results: [] }));
  }, [page]);

  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="text-center mb-4">
        <span className="insove-subtle-chip">total {data.count} users</span>
      </div>
      <ul className="list-unstyled m-0 d-flex flex-column gap-2">
        {data.results.length === 0 && (
          <li className="text-muted py-2 text-center">No users yet.</li>
        )}
        {data.results.map((u) => (
          <li key={u.id} className="dashboard-item">
            <Link to={`/users/${u.username}`} className="text-decoration-none d-block">
              <div className="insove-item d-flex justify-content-between align-items-center py-2 px-3">
                <div className="text-truncate me-2">
                  <i className="bi bi-person-circle me-2 text-secondary" />
                  <span className="fw-bold text-dark">{u.username}</span>
                  {u.email && <small className="text-muted ms-2">{u.email}</small>}
                  <small className="text-muted">
                    {" · Joined "}{new Date(u.date_joined).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </small>
                </div>
                <div className="d-flex align-items-center gap-2 text-nowrap">
                  <RoleBadge role={u.profile?.role} />
                  {u.profile?.role === "user" && <span className="badge bg-secondary">User</span>}
                  <small className="text-muted">{u.post_count} post{u.post_count !== 1 ? "s" : ""}</small>
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

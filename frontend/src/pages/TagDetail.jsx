import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { fetchTag } from "../api/client";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import Navbar from "../components/Navbar";

export default function TagDetail() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1");

  useEffect(() => {
    setData(null);
    fetchTag(slug, page)
      .then(setData)
      .catch(() => setNotFound(true));
  }, [slug, page]);

  if (notFound) return <div className="alert alert-danger">Tag not found.</div>;
  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="d-flex justify-content-center align-items-center gap-2 flex-wrap mb-4">
        <span
          className="insove-subtle-chip"
          style={{ color: "#13795b", background: "#dff7f2", border: "1px solid #b7ece2" }}
        >
          {data.tag.name}
        </span>
        <span className="insove-subtle-chip">total {data.count} posts</span>
      </div>

      <ul className="list-unstyled m-0 d-flex flex-column gap-2">
        {data.results.length === 0 && (
          <li className="text-muted py-2 text-center">No posts with this tag yet.</li>
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
                    {" · "}{new Date(post.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </div>
                  <StatusBadge status={post.status} />
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

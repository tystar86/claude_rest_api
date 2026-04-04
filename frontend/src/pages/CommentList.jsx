import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchComments } from "../api/client";
import Pagination from "../components/Pagination";
import Navbar from "../components/Navbar";

function fmt(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export default function CommentList() {
  const [data, setData] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1", 10);

  useEffect(() => {
    fetchComments(page).then(setData).catch(() => setData({ count: 0, total_pages: 1, page, results: [] }));
  }, [page]);

  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="text-center mb-4">
        <span className="insove-subtle-chip">total {data.count} comments</span>
      </div>

      <ul className="list-unstyled m-0 d-flex flex-column gap-2">
        {data.results.length === 0 && (
          <li className="text-muted py-2 text-center">No comments yet.</li>
        )}
        {data.results.map((comment) => (
          <li key={comment.id} className="dashboard-item">
            <Link to={`/posts/${comment.post_slug}`} className="text-decoration-none d-block">
              <div className="insove-item px-3 py-2">
                <div className="text-truncate mb-1" style={{ color: "#6e7da2" }}>
                  <span style={{ color: "#1b2b54" }}>{comment.body}</span>
                  {" · by "}
                  <span style={{ color: "#2f63f5", fontWeight: 700 }}>{comment.author}</span>
                  {" · "}{fmt(comment.created_at)}
                </div>
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  <span className="insove-subtle-chip">On post: {comment.post_title}</span>
                  <span className="insove-pill text-nowrap" style={{ color: "#2f8fd8", background: "#e8f6ff" }}>
                    {comment.likes} like{comment.likes !== 1 ? "s" : ""} · {comment.dislikes} dislike{comment.dislikes !== 1 ? "s" : ""}
                  </span>
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

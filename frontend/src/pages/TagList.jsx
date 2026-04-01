import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createTag, deleteTag, fetchTags, updateTag } from "../api/client";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";

export default function TagList() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [newTagName, setNewTagName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const role = user?.profile?.role;
  const canManageTags = role === "moderator" || role === "admin";

  const loadAllTags = async () => {
    setData(null);
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
    return { count: firstPage.count, results: allResults };
  };

  useEffect(() => {
    let cancelled = false;
    loadAllTags().then((next) => {
      if (!cancelled) setData(next);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreateTag = async (e) => {
    e.preventDefault();
    const name = newTagName.trim();
    if (!name) return;
    setSaving(true);
    setError("");
    try {
      await createTag(name);
      setNewTagName("");
      setData(await loadAllTags());
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create tag.");
    } finally {
      setSaving(false);
    }
  };

  const handleEditTag = async (tag) => {
    const nextName = window.prompt("Edit tag name", tag.name);
    if (!nextName || nextName.trim() === tag.name) return;
    try {
      await updateTag(tag.slug, nextName.trim());
      setData(await loadAllTags());
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to update tag.");
    }
  };

  const handleDeleteTag = async (tag) => {
    if (!window.confirm(`Delete tag "${tag.name}"?`)) return;
    try {
      await deleteTag(tag.slug);
      setData(await loadAllTags());
    } catch (err) {
      window.alert(err?.response?.data?.detail || "Failed to delete tag.");
    }
  };

  if (!data) return <div className="text-center py-5"><div className="spinner-border" /></div>;

  return (
    <div className="insove-shell w-100 insove-content-inset py-3">
      <div className="mb-4">
        <Navbar fluid />
      </div>
      <div className="text-center mb-4">
        <span className="insove-subtle-chip">total {data.count} tags</span>
      </div>
      {canManageTags && (
        <form className="insove-panel mb-3 p-3 p-md-4" onSubmit={handleCreateTag}>
          <label className="form-label fw-semibold mb-2" style={{ color: "#173f88" }}>
            Create new tag
          </label>
          <div className="d-flex align-items-center gap-2">
            <input
              className="form-control insove-form-control"
              placeholder="Tag name"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              disabled={saving}
            />
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Creating..." : "Create"}
            </button>
          </div>
          {error && <div className="text-danger small mt-2">{error}</div>}
        </form>
      )}
      <ul className="list-unstyled m-0 d-flex flex-row flex-wrap gap-2 gap-md-3 align-items-center">
        {data.results.length === 0 && (
          <li className="text-muted py-2">No tags yet.</li>
        )}
        {data.results.map((tag) => (
          <li key={tag.id} className="dashboard-item">
            <Link to={`/tags/${tag.slug}`} className="text-decoration-none">
              <span
                className="rounded-pill fw-semibold"
                style={{
                  color: "#13795b",
                  background: "rgba(23, 158, 139, 0.18)",
                  border: "1px solid rgba(19, 138, 121, 0.45)",
                  padding: "0.3rem 0.72rem",
                }}
              >
                <span style={{ color: "#0b4d36" }}>{tag.name}</span>
                <span style={{ color: "#13795b" }}> ({tag.post_count} posts)</span>
              </span>
            </Link>
            {canManageTags && (
              <span className="ms-2 d-inline-flex align-items-center gap-1">
                <button
                  className="btn btn-sm py-0 px-2"
                  type="button"
                  onClick={() => handleEditTag(tag)}
                  style={{ border: "1px solid #d8e2ff", color: "#2f63f5", background: "rgba(255,255,255,0.82)" }}
                >
                  Edit
                </button>
                <button
                  className="btn btn-sm py-0 px-2"
                  type="button"
                  onClick={() => handleDeleteTag(tag)}
                  style={{ border: "1px solid #f4c8d0", color: "#c72855", background: "rgba(255,255,255,0.82)" }}
                >
                  Delete
                </button>
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

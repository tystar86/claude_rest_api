import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createTag, deleteTag, fetchTags, updateTag } from "../api/client";
import { useAuth } from "../context/AuthContext";

const TAG_COLORS = [
  { background: "var(--sage)" },
  { background: "var(--rose)" },
  { background: "var(--bg)" },
  { background: "var(--bg-mid)" },
  { background: "var(--white)" },
];

export default function TagList() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const canManageTags = user?.can_manage_tags === true;

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
      restPages.forEach((p) => { allResults = allResults.concat(p.results); });
    }
    return { count: firstPage.count, results: allResults };
  };

  useEffect(() => {
    let cancelled = false;
    loadAllTags()
      .then((next) => { if (!cancelled) setData(next); })
      .catch(() => { if (!cancelled) setData({ count: 0, results: [] }); });
    return () => { cancelled = true; };
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
    if (!nextName || nextName.trim().toLowerCase() === tag.name.toLowerCase()) return;
    try {
      await updateTag(tag.slug, nextName.trim().toLowerCase());
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

  if (!data) return (
    <div className="nb-layout-full nb-spinner"><div className="spinner-border" /></div>
  );

  return (
    <div className="nb-layout-full">

      {/* Hero bar */}
      <div className="nb-hero-bar">
        <div className="nb-hero-count">{data.count}</div>
        <div>
          <div className="nb-hero-label">Tags Available</div>
          <div className="nb-hero-desc">Browse all tags to discover posts by topic.</div>
        </div>
      </div>

      {/* Section bar */}
      <div className="nb-section-bar" style={{ justifyContent: "space-between" }}>
        <span className="nb-section-title">All Tags</span>
        {user && (
          <button
            className="nb-btn nb-btn-sm"
            type="button"
            onClick={() => setShowCreate((v) => !v)}
            style={{ background: showCreate ? "var(--white)" : "var(--black)", color: showCreate ? "var(--black)" : "var(--sage)" }}
          >
            {showCreate ? "Cancel" : "+ New Tag"}
          </button>
        )}
      </div>

      {/* Create tag form */}
      {user && showCreate && (
        <div style={{ borderBottom: "var(--border)", padding: "20px var(--nb-copy-pad-x)", background: "var(--white)" }}>
          <form onSubmit={handleCreateTag}>
            <div style={{ display: "flex", gap: "0", maxWidth: "480px" }}>
              <input
                className="nb-input"
                style={{ flex: 1 }}
                placeholder="Tag name (lowercase)"
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value.toLowerCase())}
                disabled={saving}
              />
              <button className="nb-btn" type="submit" disabled={saving} style={{ borderLeft: "none" }}>
                {saving ? "Creating..." : "Create"}
              </button>
            </div>
            {error && <div className="alert alert-danger mt-3">{error}</div>}
          </form>
        </div>
      )}

      {/* Tag grid */}
      <div style={{ padding: "32px var(--nb-copy-pad-x)", background: "var(--bg)" }}>
        {data.results.length === 0 && (
          <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "13px", opacity: 0.5 }}>No tags yet.</div>
        )}
        <div className="nb-tag-grid" style={{ gap: "10px" }}>
          {data.results.map((tag, i) => (
            <div key={tag.id} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Link
                to={`/tags/${tag.slug}`}
                className="nb-tag-btn"
                style={TAG_COLORS[i % TAG_COLORS.length]}
              >
                {tag.name}
                <span style={{ marginLeft: "6px", opacity: 0.6 }}>({tag.post_count})</span>
              </Link>
              {canManageTags && (
                <>
                  <button
                    className="nb-btn nb-btn-sm nb-btn-secondary"
                    type="button"
                    onClick={() => handleEditTag(tag)}
                  >
                    Edit
                  </button>
                  <button
                    className="nb-btn nb-btn-sm nb-btn-danger"
                    type="button"
                    onClick={() => handleDeleteTag(tag)}
                  >
                    Del
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

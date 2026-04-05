export default function StatusBadge({ status }) {
  const isPublished = status === "published";
  return (
    <span className={isPublished ? "nb-status-live" : "nb-status-draft"}>
      {isPublished ? "Live" : "Draft"}
    </span>
  );
}

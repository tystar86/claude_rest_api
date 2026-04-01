export default function StatusBadge({ status }) {
  const isPublished = status === "published";
  return (
    <span
      className="badge"
      style={
        isPublished
          ? { color: "#13795b", background: "#dff7f2", border: "1px solid #b7ece2" }
          : { color: "#4f5b85", background: "#e9edfb", border: "1px solid #d2daf5" }
      }
    >
      {status}
    </span>
  );
}

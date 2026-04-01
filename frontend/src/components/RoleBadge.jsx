export default function RoleBadge({ role }) {
  if (!role || role === "user") return null;
  const styles = {
    admin: { color: "#b42318", background: "#fdeceb", border: "1px solid #f6c7c4" },
    moderator: { color: "#9a6700", background: "#fff7e8", border: "1px solid #f4ddad" },
  };
  return (
    <span className="badge" style={styles[role] ?? { color: "#4f5b85", background: "#e9edfb", border: "1px solid #d2daf5" }}>
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </span>
  );
}

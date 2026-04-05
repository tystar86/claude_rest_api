export default function RoleBadge({ role }) {
  if (!role || role === "user") return null;
  const cls = role === "admin" ? "nb-role-admin" : "nb-role-moderator";
  return (
    <span className={cls}>
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </span>
  );
}

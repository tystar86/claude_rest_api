import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar({ fluid = false }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/dashboard");
  };

  return (
    <nav className="navbar navbar-expand-lg site-navbar">
      <div className={fluid ? "container-fluid px-0" : "container"}>
        <Link className="navbar-brand fw-bold" to="/dashboard">TheBlog</Link>
        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
          <span className="navbar-toggler-icon" />
        </button>
        <div className="collapse navbar-collapse" id="navMenu">
          <div className="me-auto" />
          <ul className="navbar-nav ms-auto align-items-center gap-2">
            {user ? (
              <>
                <li className="nav-item">
                  <span className="navbar-text nav-user-chip">
                    <i className="bi bi-person-circle me-1" />
                    {user.username}
                    {user.profile?.role !== "user" && (
                      <span className="badge bg-warning text-dark ms-1">
                        {user.profile?.role}
                      </span>
                    )}
                  </span>
                </li>
                <li className="nav-item">
                  <button className="btn nav-auth-btn nav-auth-btn-secondary btn-sm" onClick={handleLogout}>
                    <i className="bi bi-box-arrow-right me-1" />Logout
                  </button>
                </li>
              </>
            ) : (
              <>
                <li className="nav-item">
                  <Link to="/login" className="btn nav-auth-btn nav-auth-btn-secondary btn-sm">
                    <i className="bi bi-box-arrow-in-right me-1" />Login
                  </Link>
                </li>
                <li className="nav-item">
                  <Link to="/register" className="btn nav-auth-btn nav-auth-btn-primary btn-sm">
                    <i className="bi bi-person-plus me-1" />Register
                  </Link>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
}

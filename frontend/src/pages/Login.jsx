import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await loginUser(form.email, form.password);
      setUser(user);
      navigate("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail ?? "Login failed.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="nb-auth-page">
        <div className="nb-auth-box">
          <div className="nb-auth-header">Login</div>
          <div className="nb-auth-body">
            {error && <div className="alert alert-danger mb-4">{error}</div>}
            <form onSubmit={submit}>
              <div className="nb-field">
                <label htmlFor="login-email">Email</label>
                <input
                  id="login-email"
                  type="email"
                  name="email"
                  className="nb-input"
                  value={form.email}
                  onChange={handle}
                  required
                />
              </div>
              <div className="nb-field">
                <label htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  name="password"
                  className="nb-input"
                  value={form.password}
                  onChange={handle}
                  required
                />
              </div>
              <button type="submit" className="nb-btn nb-btn-full" disabled={loading}>
                {loading ? (
                  <span className="spinner-border spinner-border-sm me-2" />
                ) : null}
                Login
              </button>
            </form>

            <p style={{ textAlign: "center", marginTop: "20px", marginBottom: 0, fontFamily: "'Space Mono', monospace", fontSize: "12px" }}>
              No account?{" "}
              <Link to="/register" style={{ color: "var(--black)", fontWeight: 700 }}>
                Register
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

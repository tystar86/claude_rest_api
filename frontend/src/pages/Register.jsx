import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GOOGLE_LOGIN_URL, registerUser } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await registerUser(form.email, form.username, form.password);
      setUser(user);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="insove-page row justify-content-center">
      <div className="col-md-5 align-self-center">
        <div className="insove-panel">
          <div className="card-body p-4">
            <h3 className="card-title fw-bold mb-4 text-center">Create Account</h3>
            {error && <div className="alert alert-danger">{error}</div>}
            <form onSubmit={submit}>
              <div className="mb-3">
                <label className="form-label fw-medium">Email</label>
                <input type="email" name="email" className="form-control insove-form-control" value={form.email} onChange={handle} required />
              </div>
              <div className="mb-3">
                <label className="form-label fw-medium">Username</label>
                <input type="text" name="username" className="form-control insove-form-control" value={form.username} onChange={handle} required />
              </div>
              <div className="mb-3">
                <label className="form-label fw-medium">Password</label>
                <input type="password" name="password" className="form-control insove-form-control" value={form.password} onChange={handle} required />
              </div>
              <div className="d-grid mt-4">
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <span className="spinner-border spinner-border-sm me-2" /> : <i className="bi bi-person-plus me-1" />}
                  Register
                </button>
              </div>
            </form>
            <hr className="my-4" />
            <div className="d-grid">
              <a href={GOOGLE_LOGIN_URL} className="btn btn-outline-danger">
                <i className="bi bi-google me-1" />Continue with Google
              </a>
            </div>
            <p className="text-center mt-3 mb-0">
              Already have an account? <Link to="/login">Login</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

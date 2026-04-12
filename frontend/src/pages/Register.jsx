import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GOOGLE_LOGIN_URL, registerUser } from "../api/client";
import { useAuth } from "../context/AuthContext";
import useResendVerification from "../hooks/useResendVerification";

export default function Register() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");
  const { resendMessage, resendIsError, resending, handleResend, clearResend } =
    useResendVerification();

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setNeedsVerification(false);
    setPendingEmail("");
    clearResend();
    setLoading(true);
    try {
      const result = await registerUser(form.email, form.username, form.password);
      if (result?.code === "verification_pending") {
        setSuccess(
          result?.detail ??
            "Registration successful. Please check your email to verify your account."
        );
        setNeedsVerification(true);
        setPendingEmail(form.email);
        setForm({ email: "", username: "", password: "" });
      } else if (result?.username) {
        setUser(result);
        navigate("/dashboard");
      } else {
        setSuccess(result?.detail ?? "Registration successful.");
        setForm({ email: "", username: "", password: "" });
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="nb-auth-page">
        <div className="nb-auth-box">
          <div className="nb-auth-header">Create Account</div>
          <div className="nb-auth-body">
            {error && <div className="alert alert-danger mb-4">{error}</div>}
            {success && (
              <div className="alert alert-success mb-4">
                {success}
                {needsVerification && (
                  <button
                    type="button"
                    className="nb-btn nb-btn-secondary mt-3"
                    style={{ display: "block", width: "100%", fontSize: "12px" }}
                    onClick={() => handleResend(pendingEmail)}
                    disabled={resending}
                  >
                    {resending ? (
                      <span className="spinner-border spinner-border-sm me-2" />
                    ) : null}
                    Resend verification email
                  </button>
                )}
              </div>
            )}
            {resendMessage && (
              <div className={`alert mb-4 ${resendIsError ? "alert-danger" : "alert-success"}`}>
                {resendMessage}
              </div>
            )}
            <form onSubmit={submit}>
              <div className="nb-field">
                <label htmlFor="reg-email">Email</label>
                <input
                  id="reg-email"
                  type="email"
                  name="email"
                  className="nb-input"
                  value={form.email}
                  onChange={handle}
                  required
                />
              </div>
              <div className="nb-field">
                <label htmlFor="reg-username">Username</label>
                <input
                  id="reg-username"
                  type="text"
                  name="username"
                  className="nb-input"
                  value={form.username}
                  onChange={handle}
                  required
                />
              </div>
              <div className="nb-field">
                <label htmlFor="reg-password">Password</label>
                <input
                  id="reg-password"
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
                Register
              </button>
            </form>

            <hr className="nb-divider" />

            <a href={GOOGLE_LOGIN_URL} className="nb-btn nb-btn-full nb-btn-secondary" style={{ display: "block", textAlign: "center" }}>
              Continue with Google
            </a>

            <p style={{ textAlign: "center", marginTop: "20px", marginBottom: 0, fontFamily: "'Space Mono', monospace", fontSize: "12px" }}>
              Already have an account?{" "}
              <Link to="/login" style={{ color: "var(--black)", fontWeight: 700 }}>
                Login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GOOGLE_LOGIN_URL, loginUser } from "../api/client";
import { useAuth } from "../context/AuthContext";
import useResendVerification from "../hooks/useResendVerification";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [pendingVerificationEmail, setPendingVerificationEmail] = useState("");
  const { resendMessage, resendIsError, resending, handleResend, clearResend } =
    useResendVerification();

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const submittedEmail = form.email;
    setError(null);
    setNeedsVerification(false);
    setPendingVerificationEmail("");
    clearResend();
    setLoading(true);
    try {
      const user = await loginUser(submittedEmail, form.password);
      setUser(user);
      navigate("/dashboard");
    } catch (err) {
      const needsEmailVerification = err.response?.data?.code === "email_not_verified";
      const detail = err.response?.data?.detail ?? "Login failed.";
      setNeedsVerification(needsEmailVerification);
      setPendingVerificationEmail(needsEmailVerification ? submittedEmail : "");
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
            {error && (
              <div className="alert alert-danger mb-4">
                {error}
                {needsVerification && (
                  <button
                    type="button"
                    className="nb-btn nb-btn-secondary mt-3"
                    style={{ display: "block", width: "100%", fontSize: "12px" }}
                    onClick={() => handleResend(pendingVerificationEmail)}
                    disabled={resending || !pendingVerificationEmail}
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

            <hr className="nb-divider" />

            <a href={GOOGLE_LOGIN_URL} className="nb-btn nb-btn-full nb-btn-secondary" style={{ display: "block", textAlign: "center" }}>
              Continue with Google
            </a>

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

import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import Card from "../components/Card";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function Login() {
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from && from.startsWith("/") && from !== "/login" ? from : "/"} replace />;
  }

  const registering = mode === "register";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next: { email?: string; password?: string } = {};
    if (!EMAIL_RE.test(email.trim())) next.email = "Enter a valid email address.";
    if (password.length < 8) next.password = "Password must be at least 8 characters.";
    else if (password.length > 128) next.password = "Password must be at most 128 characters.";
    setErrors(next);
    setFormError(null);
    if (next.email || next.password) return;

    setSubmitting(true);
    try {
      if (registering) await register(email.trim(), password);
      else await login(email.trim(), password);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  function toggle() {
    setMode(registering ? "signin" : "register");
    setErrors({});
    setFormError(null);
  }

  return (
    <div className="auth-wrap">
      <Card className="auth-card">
        <h1>{registering ? "Create account" : "Sign in"}</h1>
        <p className="muted">F&amp;O Portfolio Tracker</p>
        <form onSubmit={onSubmit} noValidate>
          {formError && (
            <div className="banner banner-error" role="alert">
              {formError}
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={errors.email ? true : undefined}
            />
            {errors.email && <div className="field-error">{errors.email}</div>}
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={errors.password ? true : undefined}
            />
            {errors.password && <div className="field-error">{errors.password}</div>}
          </div>
          <button type="submit" className="btn-primary" disabled={submitting} style={{ width: "100%" }}>
            {submitting ? "Please wait…" : registering ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className="muted" style={{ marginBottom: 0 }}>
          {registering ? "Already have an account? " : "New here? "}
          <button type="button" onClick={toggle} style={{ border: 0, background: "none", color: "var(--primary)", padding: 0 }}>
            {registering ? "Sign in" : "Create account"}
          </button>
        </p>
      </Card>
    </div>
  );
}

import React, { useState } from "react";
import Icon from "./Icon.jsx";
import { registrationError, requestJson } from "./inventory.js";

export default function RegisterPage({ onSignedIn, onShowSignIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const problem = registrationError(username, password, confirm);
    if (problem) {
      setError(problem);
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const session = await requestJson("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      onSignedIn(session.user);
    } catch (requestError) {
      setError(requestError.message);
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit} noValidate>
        <div className="brand login-brand">
          <span className="brand-mark"><Icon name="stockroom" size={18} /></span>
          <span>Stockroom</span>
        </div>
        <h1>Create an account</h1>
        <p className="login-sub">Choose a username and password to start using Stockroom.</p>

        {error && (
          <div className="error-banner" role="alert">
            <Icon name="alert" size={18} />
            <span>{error}</span>
          </div>
        )}

        <label className="field">
          <span>Username</span>
          <span className="field-input">
            <Icon name="users" size={16} />
            <input
              name="username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={submitting}
              aria-invalid={Boolean(error) || undefined}
            />
          </span>
          <span className="field-hint">3–32 letters, numbers, dots, dashes or underscores.</span>
        </label>

        <label className="field">
          <span>Password</span>
          <span className="field-input">
            <Icon name="lock" size={16} />
            <input
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={submitting}
              aria-invalid={Boolean(error) || undefined}
            />
            <button
              type="button"
              className="field-toggle"
              onClick={() => setShowPassword((shown) => !shown)}
              aria-pressed={showPassword}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </span>
          <span className="field-hint">At least 8 characters.</span>
        </label>

        <label className="field">
          <span>Confirm password</span>
          <span className="field-input">
            <Icon name="lock" size={16} />
            <input
              name="confirm-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              disabled={submitting}
              aria-invalid={Boolean(error) || undefined}
            />
          </span>
        </label>

        <button type="submit" className="button button-primary login-submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>

        <p className="login-switch">
          Already have an account?{" "}
          <button type="button" className="link-button" onClick={onShowSignIn} disabled={submitting}>
            Sign in
          </button>
        </p>
      </form>
    </main>
  );
}
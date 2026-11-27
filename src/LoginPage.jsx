import React, { useState } from "react";
import Icon from "./Icon.jsx";
import { requestJson } from "./inventory.js";

export default function LoginPage({ onSignedIn, notice = "" }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const session = await requestJson("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      onSignedIn(session.user);
    } catch (requestError) {
      setError(requestError.message);
      setPassword("");
      setSubmitting(false);
    }
  }

  const message = error || notice;

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit} noValidate>
        <div className="brand login-brand">
          <span className="brand-mark"><Icon name="stockroom" size={18} /></span>
          <span>Stockroom</span>
        </div>
        <h1>Sign in</h1>
        <p className="login-sub">Sign in to view stock, customer balances and the assistant.</p>

        {message && (
          <div className={error ? "error-banner" : "login-notice"} role="alert">
            <Icon name="alert" size={18} />
            <span>{message}</span>
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
        </label>

        <label className="field">
          <span>Password</span>
          <span className="field-input">
            <Icon name="lock" size={16} />
            <input
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
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
        </label>

        <button type="submit" className="button button-primary login-submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

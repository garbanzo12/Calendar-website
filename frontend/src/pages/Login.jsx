import { useState } from "react";

import apiClient from "../api/client";
import { getApiErrorMessage } from "../api/errors";

export default function Login() {
  const [error, setError] = useState("");
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);

  const handleGoogleLogin = async () => {
    setError("");
    setIsGoogleSubmitting(true);

    try {
      const response = await apiClient.get("/auth/google/login");
      window.location.href = response.data.auth_url;
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Google login is not available."));
      setIsGoogleSubmitting(false);
    }
  };

  return (
    <main className="page-shell auth-page">
      <section className="auth-hero">
        <p className="eyebrow">Personal AI Calendar</p>
        <h1>Talk to your calendar like it already knows your day.</h1>
        <p>
          Sign in to turn plain-language requests into tasks and calendar events synced with your backend.
        </p>
      </section>

      <section className="auth-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Secure access</p>
            <h2>Sign in with Google</h2>
          </div>
        </div>

        <div className="auth-form">
          {error ? <p className="status-text error-text">{error}</p> : null}

          <button className="ghost-button full-width google-login-button" disabled={isGoogleSubmitting} onClick={handleGoogleLogin} type="button">
            <svg aria-hidden="true" className="google-icon" viewBox="0 0 24 24">
              <path d="M22.5 12.24c0-.81-.07-1.59-.21-2.34H12v4.43h5.89a5.04 5.04 0 0 1-2.18 3.31v2.74h3.52c2.06-1.9 3.27-4.69 3.27-8.14z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.27-2.62l-3.52-2.74c-.98.66-2.23 1.05-3.75 1.05-2.88 0-5.32-1.94-6.19-4.55H2.17v2.82A10.99 10.99 0 0 0 12 23z" fill="#34A853" />
              <path d="M5.81 14.14A6.62 6.62 0 0 1 5.46 12c0-.74.13-1.46.35-2.14V7.04H2.17A11 11 0 0 0 1 12c0 1.79.43 3.48 1.17 4.96l3.64-2.82z" fill="#FBBC05" />
              <path d="M12 5.31c1.62 0 3.07.56 4.21 1.65l3.15-3.15C17.46 2.03 14.97 1 12 1 7.69 1 3.99 3.47 2.17 7.04l3.64 2.82c.87-2.61 3.31-4.55 6.19-4.55z" fill="#EA4335" />
            </svg>
            {isGoogleSubmitting ? "Connecting to Google..." : "Continue with Google"}
          </button>
        </div>
      </section>
    </main>
  );
}

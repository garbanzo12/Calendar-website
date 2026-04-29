import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import apiClient from "../api/client";
<<<<<<< HEAD
import { getApiErrorMessage } from "../api/errors";
import { syncCalendar } from "../api/calendarService";
=======
>>>>>>> parent of 4a8ac17 (Merge pull request #8 from garbanzo12/latency-2)
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await apiClient.post("/auth/login", form);
      const token = response.data.access_token;
      login(token, response.data.user);

      apiClient
        .post("/calendar/sync", null, {
          headers: { Authorization: `Bearer ${token}` },
        })
        .then(() => console.log("Calendar synced successfully"))
        .catch((err) => console.error("Calendar sync failed:", err));

      navigate("/dashboard");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Login failed."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError("");

    try {
      const response = await apiClient.get("/auth/google/login");
      window.location.href = response.data.auth_url;
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Google login is not available."));
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
            <p className="eyebrow">Welcome back</p>
            <h2>Login</h2>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input name="email" onChange={handleChange} required type="email" value={form.email} />
          </label>
          <label>
            Password
            <input name="password" onChange={handleChange} required type="password" value={form.password} />
          </label>

          {error ? <p className="status-text error-text">{error}</p> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Logging in..." : "Login"}
          </button>
          <button className="ghost-button full-width" onClick={handleGoogleLogin} type="button">
            Login with Google
          </button>
        </form>

        <p className="switch-link">
          Need an account? <Link to="/register">Register</Link>
        </p>
      </section>
    </main>
  );
}

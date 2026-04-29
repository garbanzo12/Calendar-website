import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import apiClient from "../api/client";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
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
      const response = await apiClient.post("/auth/register", form);
      login(response.data.access_token, response.data.user);
      navigate("/dashboard");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Registration failed."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="page-shell auth-page">
      <section className="auth-hero">
        <p className="eyebrow">Get started</p>
        <h1>Build your day with a chat-first calendar workspace.</h1>
        <p>Create your account and start scheduling tasks from plain text in seconds.</p>
      </section>

      <section className="auth-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">New account</p>
            <h2>Register</h2>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Name
            <input name="name" onChange={handleChange} required type="text" value={form.name} />
          </label>
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
            {isSubmitting ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="switch-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </section>
    </main>
  );
}

import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

function ProtectedRoute({ children }) {
  const { token, authReady } = useAuth();

  if (!authReady) {
    return <div className="page-shell centered-panel">Loading session...</div>;
  }

  return token ? children : <Navigate to="/login" replace />;
}

function GuestRoute({ children }) {
  const { token, authReady } = useAuth();

  if (!authReady) {
    return <div className="page-shell centered-panel">Loading session...</div>;
  }

  return token ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  const { token } = useAuth();
  const [theme, setTheme] = useState(() => localStorage.getItem("calendar_theme") || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("calendar_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"));
  };

  return (
    <div className="app-shell">
      <Navbar isAuthenticated={Boolean(token)} isDarkTheme={theme === "dark"} onToggleTheme={toggleTheme} />
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <Login />
            </GuestRoute>
          }
        />
        <Route path="/register" element={<Navigate to="/login" replace />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard isDarkTheme={theme === "dark"} onToggleTheme={toggleTheme} />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </div>
  );
}

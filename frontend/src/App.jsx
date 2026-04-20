import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";

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

  return (
    <div className="app-shell">
      <Navbar isAuthenticated={Boolean(token)} />
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <Login />
            </GuestRoute>
          }
        />
        <Route
          path="/register"
          element={
            <GuestRoute>
              <Register />
            </GuestRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </div>
  );
}

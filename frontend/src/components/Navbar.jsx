import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Navbar({ isAuthenticated }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="navbar">
      <Link className="brand" to={isAuthenticated ? "/dashboard" : "/login"}>
        <span className="brand-mark">AI</span>
        <div>
          <strong>Personal Calendar</strong>
          <p>Plan by conversation</p>
        </div>
      </Link>

      <nav className="nav-actions">
        {isAuthenticated ? (
          <>
            <div className="user-chip">
              <span>{user?.name?.[0] || "U"}</span>
              <div>
                <strong>{user?.name || "User"}</strong>
                <p>{user?.email}</p>
              </div>
            </div>
            <button className="ghost-button" onClick={handleLogout} type="button">
              Logout
            </button>
          </>
        ) : (
          <>
            <Link className="ghost-button" to="/login">
              Login
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}

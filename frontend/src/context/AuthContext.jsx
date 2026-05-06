import { createContext, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import apiClient from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    const storedToken = localStorage.getItem("calendar_token");
    const storedUser = localStorage.getItem("calendar_user");

    if (storedToken) {
      setToken(storedToken);
    }

    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem("calendar_user");
      }
    }

    setAuthReady(true);
  }, []);

  useEffect(() => {
    const hashParams = new URLSearchParams(location.hash.substring(1));
    const callbackToken = hashParams.get("token");
    const email = hashParams.get("email");
    const name = hashParams.get("name");

    if (!callbackToken) {
      return;
    }

    const nextUser = {
      name: name || email?.split("@")[0] || "Google User",
      email: email || "",
    };

    login(callbackToken, nextUser);

    window.history.replaceState(null, "", "/dashboard");

    apiClient
      .post("/calendar/sync", null, {
        headers: { Authorization: `Bearer ${callbackToken}` },
      })
      .then(() => console.log("Calendar synced successfully"))
      .catch((err) => console.error("Calendar sync failed:", err));

    navigate("/dashboard", { replace: true });
  }, [location.search, navigate]);

  const login = (nextToken, nextUser) => {
    setToken(nextToken);
    setUser(nextUser);
    localStorage.setItem("calendar_token", nextToken);
    localStorage.setItem("calendar_user", JSON.stringify(nextUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("calendar_token");
    localStorage.removeItem("calendar_user");
  };

  return (
    <AuthContext.Provider
      value={{
        authReady,
        token,
        user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}

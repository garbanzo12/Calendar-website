import { createContext, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

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
    const params = new URLSearchParams(location.search);
    const callbackToken = params.get("token");
    const email = params.get("email");
    const name = params.get("name");

    if (!callbackToken) {
      return;
    }

    const nextUser = {
      name: name || email?.split("@")[0] || "Google User",
      email: email || "",
    };

    login(callbackToken, nextUser);
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

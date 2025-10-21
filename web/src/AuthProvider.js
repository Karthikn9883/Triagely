import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext();

// API base URL from environment variable
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ─────────────────────────────────────────────
     1️⃣  On page load, check if we have a token and validate it
  ────────────────────────────────────────────────*/
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    // Verify token by calling /auth/me
    fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Invalid token");
        return res.json();
      })
      .then((userData) => {
        setUser({
          ...userData,
          token,
        });
      })
      .catch(() => {
        // Invalid token, remove it
        localStorage.removeItem("access_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  /* ─────────────────────────────────────────────
     2️⃣  Sign up - Register a new user
  ────────────────────────────────────────────────*/
  const signUp = async (email, password, name) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, name }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Registration failed");
    }

    const data = await response.json();

    // Store token and set user
    localStorage.setItem("access_token", data.access_token);
    setUser({
      user_id: data.user_id,
      email: data.email,
      name: data.name,
      username: data.name || data.email.split("@")[0],
      token: data.access_token,
    });

    return data;
  };

  /* ─────────────────────────────────────────────
     3️⃣  Confirmation - No longer needed for local auth
         (kept for compatibility)
  ────────────────────────────────────────────────*/
  const confirmSignUp = async (email, code) => {
    // No-op for local auth - registration is immediate
    return Promise.resolve();
  };

  /* ─────────────────────────────────────────────
     4️⃣  Sign in - Login to existing account
  ────────────────────────────────────────────────*/
  const signIn = async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Login failed");
    }

    const data = await response.json();

    // Store token and set user
    localStorage.setItem("access_token", data.access_token);
    setUser({
      user_id: data.user_id,
      email: data.email,
      name: data.name,
      username: data.name || data.email.split("@")[0],
      token: data.access_token,
    });

    return data;
  };

  /* ─────────────────────────────────────────────
     5️⃣  Sign out
  ────────────────────────────────────────────────*/
  const signOut = async () => {
    localStorage.removeItem("access_token");
    setUser(null);
  };

  /* ─────────────────────────────────────────────
     6️⃣  Get ID Token - Returns the JWT token for API calls
  ────────────────────────────────────────────────*/
  const getIdToken = async () => {
    return localStorage.getItem("access_token");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signUp,
        confirmSignUp,
        signIn,
        signOut,
        getIdToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

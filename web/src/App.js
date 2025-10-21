import React, { useState } from "react";
import { useAuth } from "./AuthProvider";
import Login from "./loginPage/Login";
import Signup from "./loginPage/Signup";
import Home from "./pages/Home";
import Connected from "./pages/Connected"; // Make sure you create this component!

import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

export default function App() {
  const { user, loading, signUp, signIn } = useAuth();
  const [authStage, setAuthStage] = useState("login");

  // Auth handlers
  const handleSignup = async (email, pw, name) => {
    await signUp(email, pw, name);
    // No confirmation step needed - user is auto-logged in
  };

  const handleLogin = async (email, pw) => {
    await signIn(email, pw);
  };

  if (loading) return <div>Loading...</div>;

  return (
    <Router>
      <Routes>
        {/* Connected route for post-OAuth */}
        <Route path="/connected" element={<Connected />} />
        {/* Auth Flow */}
        {!user ? (
          <>
            <Route
              path="/"
              element={
                authStage === "login" ? (
                  <Login onLogin={handleLogin} switchToSignup={() => setAuthStage("signup")} />
                ) : (
                  <Signup onSignup={handleSignup} switchToLogin={() => setAuthStage("login")} />
                )
              }
            />
            {/* Redirect all other routes to / */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        ) : (
          <>
            {/* Authenticated users see Home */}
            <Route path="/*" element={<Home />} />
          </>
        )}
      </Routes>
    </Router>
  );
}

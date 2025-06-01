import React, { useState } from "react";
import { useAuth } from "./AuthProvider";
import Login from "./loginPage/Login";
import Signup from "./loginPage/Signup";
import Confirm from "./loginPage/Confirm";
import Home from "./pages/Home";
import Connected from "./pages/Connected"; // Make sure you create this component!

import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

export default function App() {
  const { user, loading, signUp, confirmSignUp, signIn } = useAuth();
  const [authStage, setAuthStage] = useState("login");
  const [signupEmail, setSignupEmail] = useState("");

  // Auth handlers
  const handleSignup = async (email, pw, name) => {
    await signUp(email, pw, name);
    setSignupEmail(email);
    setAuthStage("confirm");
  };
  const handleConfirm = async (email, code) => {
    await confirmSignUp(email, code);
    setAuthStage("login");
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
                ) : authStage === "signup" ? (
                  <Signup onSignup={handleSignup} switchToLogin={() => setAuthStage("login")} />
                ) : authStage === "confirm" ? (
                  <Confirm email={signupEmail} onConfirm={handleConfirm} switchToLogin={() => setAuthStage("login")} />
                ) : null
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

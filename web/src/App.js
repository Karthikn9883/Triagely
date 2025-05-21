import React, { useState } from "react";
import { useAuth } from "./AuthProvider";
import Login from "./loginPage/Login";
import Signup from "./loginPage/Signup";
import Confirm from "./loginPage/Confirm";
import Home from "./pages/Home";

export default function App() {
  const { user, loading, signUp, confirmSignUp, signIn } = useAuth();
  const [authStage, setAuthStage] = useState("login");
  const [signupEmail, setSignupEmail] = useState("");

  if (loading) return <div>Loading...</div>;

  // Handlers (as before)
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

  // ---- Main render:
  if (!user) {
    // Show login/signup/confirm
    if (authStage === "login")
      return <Login onLogin={handleLogin} switchToSignup={() => setAuthStage("signup")} />;
    if (authStage === "signup")
      return <Signup onSignup={handleSignup} switchToLogin={() => setAuthStage("login")} />;
    if (authStage === "confirm")
      return <Confirm email={signupEmail} onConfirm={handleConfirm} switchToLogin={() => setAuthStage("login")} />;
    return null;
  } else {
    // Authenticated: show main app
    return <Home />;
  }
}
 
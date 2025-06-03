import React, { createContext, useContext, useState, useEffect } from "react";
import { Amplify, Auth } from "aws-amplify";
import awsConfig from "./aws-exports";

Amplify.configure(awsConfig);

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ─────────────────────────────────────────────
     1️⃣  On page load, find existing Cognito user
  ────────────────────────────────────────────────*/
  useEffect(() => {
    Auth.currentAuthenticatedUser()
      .then(cogUser => {
        if (!cogUser) return setUser(null);
        /* ← ✅ Inject a username prop. */
        const uName =
          cogUser.attributes?.name ||
          cogUser.attributes?.preferred_username ||
          cogUser.username ||
          cogUser.attributes?.email?.split("@")[0];
        setUser({ ...cogUser, username: uName });
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  /* ─────────────────────────────────────────────
     The sign-up / confirm helpers are unchanged
  ────────────────────────────────────────────────*/
  const signUp = async (email, password, name) => {
    await Auth.signUp({
      username: email,
      password,
      attributes: { email, name },   // you already capture “name”
    });
  };

  const confirmSignUp = async (email, code) => {
    await Auth.confirmSignUp(email, code);
  };

  /* ─────────────────────────────────────────────
     2️⃣  On sign-in, attach the username again
  ────────────────────────────────────────────────*/
  const signIn = async (email, password) => {
    const cogUser = await Auth.signIn(email, password);
    const uName =
      cogUser.attributes?.name ||
      cogUser.attributes?.preferred_username ||
      cogUser.username ||
      cogUser.attributes?.email?.split("@")[0];
    setUser({ ...cogUser, username: uName });   /* ← ✅ */
    return cogUser;
  };

  const signOut = async () => {
    await Auth.signOut();
    setUser(null);
  };

  const getIdToken = async () => {
    if (!user) return null;
    const session = await Auth.currentSession();
    return session.getIdToken().getJwtToken();
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
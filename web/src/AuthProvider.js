import React, { createContext, useContext, useState, useEffect } from "react";
import { Amplify, Auth } from "aws-amplify";
import awsConfig from "./aws-exports";

Amplify.configure(awsConfig);

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Auth.currentAuthenticatedUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // <--- accepts name attribute!
  const signUp = async (email, password, name) => {
    await Auth.signUp({
      username: email,
      password,
      attributes: { email, name },
    });
  };

  const confirmSignUp = async (email, code) => {
    await Auth.confirmSignUp(email, code);
  };

  const signIn = async (email, password) => {
    const user = await Auth.signIn(email, password);
    setUser(user);
    return user;
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

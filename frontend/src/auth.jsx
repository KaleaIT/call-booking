import React, { createContext, useContext, useState } from "react";
import { api } from "./api.js";

// Single source of truth for auth state, shared by Nav and all pages.
// Without this the app read api.isAuthed() once at first render and never
// re-rendered after login — the nav updated but the page body did not.
const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  // Treat a session as valid only if BOTH token and user are present.
  const [user, setUser] = useState(() => (api.isAuthed() ? api.currentUser() : null));

  async function login(email, password) {
    const u = await api.login(email, password);
    setUser(u);
    return u;
  }

  async function register(email, password, fullName) {
    await api.register(email, password, fullName);
    return login(email, password);
  }

  function logout() {
    api.logout();
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}

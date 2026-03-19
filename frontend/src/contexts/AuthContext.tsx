"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

const STORAGE_KEY = "tenet:user_id";

interface AuthContextValue {
  userId: string | null;
  login: (userId: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored) setUserId(stored);
    setHydrated(true);
  }, []);

  const login = useCallback((id: string) => {
    sessionStorage.setItem(STORAGE_KEY, id);
    setUserId(id);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setUserId(null);
  }, []);

  if (!hydrated) return null;

  return (
    <AuthContext.Provider
      value={{ userId, login, logout, isAuthenticated: userId !== null }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

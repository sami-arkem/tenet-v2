"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

const TOKEN_KEY = "tenet:access_token";
const META_KEY = "tenet:user_meta";

interface UserMeta {
  userId: string;
  tenantId: string;
  role: string;
}

interface AuthContextValue {
  token: string | null;
  userId: string | null;
  tenantId: string | null;
  role: string | null;
  isAuthenticated: boolean;
  loginWithToken: (token: string, meta: UserMeta) => void;
  logout: () => void;
  /** Legacy shim: dev mode login with raw user ID */
  login: (userId: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [meta, setMeta] = useState<UserMeta | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const storedToken = sessionStorage.getItem(TOKEN_KEY);
    const storedMeta = sessionStorage.getItem(META_KEY);
    if (storedToken && storedMeta) {
      try {
        setToken(storedToken);
        setMeta(JSON.parse(storedMeta));
      } catch {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(META_KEY);
      }
    }
    setHydrated(true);
  }, []);

  const loginWithToken = useCallback((t: string, m: UserMeta) => {
    sessionStorage.setItem(TOKEN_KEY, t);
    sessionStorage.setItem(META_KEY, JSON.stringify(m));
    setToken(t);
    setMeta(m);
  }, []);

  // Legacy shim for dev mode (X-User-ID header auth)
  const login = useCallback((userId: string) => {
    const m: UserMeta = { userId, tenantId: "", role: "owner" };
    sessionStorage.setItem(TOKEN_KEY, `dev:${userId}`);
    sessionStorage.setItem(META_KEY, JSON.stringify(m));
    setToken(`dev:${userId}`);
    setMeta(m);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(META_KEY);
    setToken(null);
    setMeta(null);
  }, []);

  if (!hydrated) return null;

  return (
    <AuthContext.Provider
      value={{
        token,
        userId: meta?.userId ?? null,
        tenantId: meta?.tenantId ?? null,
        role: meta?.role ?? null,
        isAuthenticated: !!token,
        loginWithToken,
        logout,
        login,
      }}
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

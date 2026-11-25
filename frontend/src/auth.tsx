import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchMe, getToken, login as apiLogin, register as apiRegister, setToken, setUnauthorizedHandler } from "./api";
import type { User } from "./api";

interface AuthState {
  user: User | null;
  token: string | null;
  /** True while a stored token is being validated on first load. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => getToken() !== null);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    setUser(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchMe()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) logout();
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  const accept = useCallback((newToken: string) => {
    setToken(newToken);
    setLoading(true);
    setTokenState(newToken);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      accept(await apiLogin(email, password));
    },
    [accept],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      accept(await apiRegister(email, password));
    },
    [accept],
  );

  const value = useMemo<AuthState>(
    () => ({ user, token, loading, login, register, logout }),
    [user, token, loading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

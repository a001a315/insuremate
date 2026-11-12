import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokenStore } from "@/services/api";
import type { TokenResponse, User } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string, hospitalName: string, hospitalCity?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  useEffect(() => {
    if (!tokenStore.get()) return;
    api<User>("/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const accept = (r: TokenResponse) => { tokenStore.set(r.access_token); setUser(r.user); };
  const login = useCallback(async (email: string, password: string) =>
    accept(await api<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })), []);
  const register = useCallback(async (email: string, full_name: string, password: string, hospital_name: string, hospital_city?: string) =>
    accept(await api<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, full_name, password, hospital_name, hospital_city: hospital_city || null }) })), []);
  const refreshUser = useCallback(async () => { setUser(await api<User>("/auth/me")); }, []);
  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout, refreshUser }), [user, loading, login, register, logout, refreshUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

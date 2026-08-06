import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On first load, if a token is already stored, verify it's still valid
  // by fetching the current user rather than trusting a stale cached copy.
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    authApi
      .fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
      })
      .finally(() => setIsLoading(false));
  }, []);

  function persistSession(token: string, nextUser: User) {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(nextUser));
    setUser(nextUser);
  }

  async function login(email: string, password: string) {
    const { access_token, user: nextUser } = await authApi.login(email, password);
    persistSession(access_token, nextUser);
  }

  async function register(email: string, password: string, fullName: string) {
    const { access_token, user: nextUser } = await authApi.register(email, password, fullName);
    persistSession(access_token, nextUser);
  }

  function logout() {
    // JWTs are stateless — "logging out" just discards the token client-side.
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

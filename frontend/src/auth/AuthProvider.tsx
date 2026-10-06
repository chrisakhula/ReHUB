import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { identityApi } from "../api/identity";
import type { User } from "../types/identity";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clear: () => void;
  can: (permission: string) => boolean;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const clear = () => {
    setUser(null);
    cache.clear();
  };
  useEffect(() => {
    let mounted = true;
    identityApi
      .me()
      .catch(() => identityApi.refresh())
      .then((u) => {
        if (mounted) setUser(u);
      })
      .catch((error) => {
        if (
          mounted &&
          !(error instanceof Error && "status" in error && error.status === 401)
        )
          setError(
            "Cannot connect to the server. Check that the backend is running.",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    const expired = () => {
      setUser(null);
      cache.clear();
    };
    window.addEventListener("session-expired", expired);
    return () => {
      mounted = false;
      window.removeEventListener("session-expired", expired);
    };
  }, [cache]);
  const login = async (email: string, password: string) => {
    const u = await identityApi.login(email, password);
    cache.clear();
    setUser(u);
    setError("");
  };
  const logout = async () => {
    await identityApi.logout();
    clear();
  };
  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        logout,
        clear,
        can: (p) => user?.permissions.includes(p) ?? false,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider missing");
  return context;
}

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import type {
  UserInfo,
  TokenResponse,
  RefreshResult,
  LoginRequest,
  RegisterRequest,
} from "@/types/auth";

interface AuthContextValue {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const API_BASE = "";

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? body.detail.map((d: { msg?: string }) => d.msg).join(", ")
          : res.statusText;
    throw Object.assign(new Error(detail), { status: res.status });
  }
  return res.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, validate stored token
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }

    apiFetch<UserInfo>("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(setUser)
      .catch(async () => {
        // Try refresh
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          try {
            const result = await apiFetch<RefreshResult>(
              "/api/v1/auth/refresh",
              {
                method: "POST",
                body: JSON.stringify({ refresh_token: refreshToken }),
              }
            );
            localStorage.setItem("access_token", result.access_token);
            const meData = await apiFetch<UserInfo>("/api/v1/auth/me", {
              headers: {
                Authorization: `Bearer ${result.access_token}`,
              },
            });
            setUser(meData);
          } catch {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
          }
        } else {
          localStorage.removeItem("access_token");
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (req: LoginRequest) => {
    const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(req),
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(data.user);
  }, []);

  const register = useCallback(async (req: RegisterRequest) => {
    const data = await apiFetch<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(req),
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

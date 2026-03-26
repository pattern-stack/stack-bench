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
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth";

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

async function fetchMe(token: string): Promise<UserInfo> {
  return apiFetch<UserInfo>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, validate stored token
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    fetchMe(token)
      .then(setUser)
      .catch(async () => {
        // Try refresh
        const refreshToken = getRefreshToken();
        if (refreshToken) {
          try {
            const result = await apiFetch<RefreshResult>(
              "/api/v1/auth/refresh",
              {
                method: "POST",
                body: JSON.stringify({ refresh_token: refreshToken }),
              }
            );
            setTokens(result.access_token, refreshToken);
            const meData = await fetchMe(result.access_token);
            setUser(meData);
          } catch {
            clearTokens();
          }
        } else {
          clearTokens();
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (req: LoginRequest) => {
    const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(req),
    });
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, []);

  const register = useCallback(async (req: RegisterRequest) => {
    const data = await apiFetch<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(req),
    });
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
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

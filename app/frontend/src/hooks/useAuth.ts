/**
 * Authentication hook for Stack Bench.
 *
 * Provides login, register, logout, and current user state.
 * Uses react-query for /auth/me and handles token refresh on 401.
 */

import { useState, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from "@/lib/auth";

interface UserInfo {
  id: string;
  reference_number: string;
  first_name: string;
  last_name: string;
  display_name: string;
  email: string;
}

interface TokenResponse {
  user: UserInfo;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthUser {
  id: string;
  reference_number: string;
  first_name: string;
  last_name: string;
  display_name: string;
  email: string;
  is_active: boolean;
}

export function useAuth() {
  const queryClient = useQueryClient();
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!getAccessToken()
  );

  const {
    data: user,
    isLoading,
    error,
  } = useQuery<AuthUser>({
    queryKey: ["auth", "me"],
    queryFn: () => apiClient.get<AuthUser>("/api/v1/auth/me"),
    enabled: isAuthenticated,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Handle 401 errors — attempt refresh before clearing tokens
  useEffect(() => {
    if (error && "status" in error && (error as { status: number }).status === 401) {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        // Try to refresh before giving up
        apiClient
          .post<{ access_token: string }>("/api/v1/auth/refresh", {
            refresh_token: refreshToken,
          })
          .then((result) => {
            setTokens(result.access_token, refreshToken);
            queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
          })
          .catch(() => {
            clearTokens();
            setIsAuthenticated(false);
            queryClient.removeQueries({ queryKey: ["auth", "me"] });
          });
      } else {
        clearTokens();
        setIsAuthenticated(false);
        queryClient.removeQueries({ queryKey: ["auth", "me"] });
      }
    }
  }, [error, queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await apiClient.post<TokenResponse>("/api/v1/auth/login", {
        email,
        password,
      });
      setTokens(result.access_token, result.refresh_token);
      setIsAuthenticated(true);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      return result;
    },
    [queryClient]
  );

  const register = useCallback(
    async (
      firstName: string,
      lastName: string,
      email: string,
      password: string
    ) => {
      const result = await apiClient.post<TokenResponse>(
        "/api/v1/auth/register",
        {
          first_name: firstName,
          last_name: lastName,
          email,
          password,
        }
      );
      setTokens(result.access_token, result.refresh_token);
      setIsAuthenticated(true);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      return result;
    },
    [queryClient]
  );

  const logout = useCallback(() => {
    clearTokens();
    setIsAuthenticated(false);
    queryClient.removeQueries({ queryKey: ["auth", "me"] });
  }, [queryClient]);

  const refresh = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      setIsAuthenticated(false);
      return false;
    }
    try {
      const result = await apiClient.post<{ access_token: string }>(
        "/api/v1/auth/refresh",
        { refresh_token: refreshToken }
      );
      setTokens(result.access_token, refreshToken);
      return true;
    } catch {
      clearTokens();
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  return {
    user: user ?? null,
    isAuthenticated: isAuthenticated && !!user,
    isLoading: isAuthenticated && isLoading,
    login,
    register,
    logout,
    refresh,
  };
}

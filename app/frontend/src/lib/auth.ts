/**
 * Token storage and auth helpers for Stack Bench.
 *
 * Stores JWT tokens in localStorage. Used by the API client
 * for Authorization headers and by useAuth hook for state management.
 */

const ACCESS_TOKEN_KEY = "sb_access_token";
const REFRESH_TOKEN_KEY = "sb_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

import { useState, useEffect, useCallback } from "react";

interface GitHubConnectionStatus {
  connected: boolean;
  github_login: string | null;
  loading: boolean;
  error: string | null;
  connect: () => void;
}

/**
 * Generate a random PKCE code_verifier (43-128 URL-safe chars).
 */
function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) =>
    byte.toString(36).padStart(2, "0")
  )
    .join("")
    .slice(0, 64);
}

export function useGitHubConnection(): GitHubConnectionStatus {
  const [connected, setConnected] = useState(false);
  const [githubLogin, setGithubLogin] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check URL params on mount for OAuth callback result
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const githubParam = params.get("github");

    if (githubParam === "connected") {
      // Clean up URL
      const url = new URL(window.location.href);
      url.searchParams.delete("github");
      window.history.replaceState({}, "", url.pathname + url.search);
    } else if (githubParam === "error") {
      const message = params.get("message") ?? "GitHub connection failed";
      setError(message);
      // Clean up URL
      const url = new URL(window.location.href);
      url.searchParams.delete("github");
      url.searchParams.delete("message");
      window.history.replaceState({}, "", url.pathname + url.search);
    }
  }, []);

  // Fetch connection status
  useEffect(() => {
    let cancelled = false;

    async function fetchStatus() {
      try {
        const response = await fetch("/api/v1/auth/github/status");
        if (!response.ok) {
          throw new Error(`Status check failed: ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setConnected(data.connected);
          setGithubLogin(data.github_login);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to check GitHub status");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  const connect = useCallback(() => {
    const codeVerifier = generateCodeVerifier();
    sessionStorage.setItem("github_code_verifier", codeVerifier);
    // Navigate to backend OAuth endpoint -- backend handles redirect to GitHub
    window.location.href = `/api/v1/auth/github?code_verifier=${encodeURIComponent(codeVerifier)}`;
  }, []);

  return {
    connected,
    github_login: githubLogin,
    loading,
    error,
    connect,
  };
}

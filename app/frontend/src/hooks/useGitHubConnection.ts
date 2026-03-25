/**
 * GitHub connection management hook.
 *
 * Provides connection status, connect (OAuth popup), and disconnect.
 */

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { setTokens } from "@/lib/auth";

interface GitHubConnectionStatus {
  connected: boolean;
  github_login: string | null;
}

interface GitHubAuthorizeResponse {
  authorize_url: string;
  state: string;
}

export function useGitHubConnection() {
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery<GitHubConnectionStatus>({
    queryKey: ["github", "status"],
    queryFn: () =>
      apiClient.get<GitHubConnectionStatus>("/api/v1/auth/github/status"),
    staleTime: 60_000,
  });

  const disconnectMutation = useMutation({
    mutationFn: () => apiClient.delete("/api/v1/auth/github"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["github", "status"] });
    },
  });

  const connect = async () => {
    // 1. Get authorize URL from backend
    const { authorize_url, state } =
      await apiClient.get<GitHubAuthorizeResponse>("/api/v1/auth/github");

    // 2. Open popup to GitHub
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      authorize_url,
      "github-oauth",
      `width=${width},height=${height},left=${left},top=${top},popup=yes`
    );

    // 3. Listen for callback message from popup
    return new Promise<void>((resolve, reject) => {
      const handleMessage = async (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type !== "github-oauth-callback") return;

        window.removeEventListener("message", handleMessage);

        const { code, state: returnedState } = event.data;
        if (returnedState !== state) {
          reject(new Error("State mismatch — possible CSRF attack"));
          return;
        }

        try {
          // 4. Exchange code for tokens via backend
          const result = await apiClient.post<{
            access_token: string;
            refresh_token: string;
          }>("/api/v1/auth/github/callback", { code, state: returnedState });

          // 5. Store JWT tokens
          setTokens(result.access_token, result.refresh_token);

          // 6. Refresh queries
          queryClient.invalidateQueries({ queryKey: ["github", "status"] });
          queryClient.invalidateQueries({ queryKey: ["auth", "me"] });

          resolve();
        } catch (err) {
          reject(err);
        }
      };

      window.addEventListener("message", handleMessage);

      // Handle popup being closed without completing
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed);
          window.removeEventListener("message", handleMessage);
          // Don't reject — user may have just closed the popup
          resolve();
        }
      }, 500);
    });
  };

  return {
    connected: status?.connected ?? false,
    githubLogin: status?.github_login ?? null,
    isLoading,
    connect,
    disconnect: disconnectMutation.mutate,
    isDisconnecting: disconnectMutation.isPending,
  };
}

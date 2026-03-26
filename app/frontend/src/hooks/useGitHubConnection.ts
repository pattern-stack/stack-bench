/**
 * GitHub connection management hook.
 *
 * Provides connection status, connect (OAuth popup), and disconnect.
 */

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

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
    // 1. Open popup immediately (must be synchronous from user click to avoid popup blocker)
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      "about:blank",
      "github-oauth",
      `width=${width},height=${height},left=${left},top=${top},popup=yes`
    );

    // 2. Get authorize URL from backend, then navigate the popup
    const { authorize_url, state } =
      await apiClient.get<GitHubAuthorizeResponse>("/api/v1/auth/github", {
        redirect_origin: window.location.origin,
      });

    if (popup) {
      popup.location.href = authorize_url;
    }

    // 3. Listen for callback message from popup
    return new Promise<void>((resolve, reject) => {
      let settled = false;

      const handleMessage = async (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type !== "github-oauth-callback") return;
        if (settled) return;
        settled = true;

        window.removeEventListener("message", handleMessage);

        const { code, state: returnedState } = event.data;
        if (returnedState !== state) {
          reject(new Error("State mismatch — possible CSRF attack"));
          return;
        }

        try {
          // 4. Exchange code via backend — stores Connection for authenticated user
          await apiClient.post("/api/v1/auth/github/callback", {
            code,
            state: returnedState,
            redirect_origin: window.location.origin,
          });

          // 5. Refresh queries
          queryClient.invalidateQueries({ queryKey: ["github", "status"] });
          queryClient.invalidateQueries({ queryKey: ["onboarding"] });

          resolve();
        } catch (err) {
          reject(err);
        }
      };

      window.addEventListener("message", handleMessage);

      // Handle popup being closed without completing.
      // Delay after detecting close to allow pending postMessage to arrive.
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed);
          // Give 1s for the postMessage to arrive before giving up
          setTimeout(() => {
            if (!settled) {
              settled = true;
              window.removeEventListener("message", handleMessage);
              resolve();
            }
          }, 1000);
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

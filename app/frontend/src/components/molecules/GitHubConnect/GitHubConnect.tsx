import { useGitHubConnection } from "@/hooks/useGitHubConnection";

export interface GitHubConnectProps {
  className?: string;
}

function GitHubConnect({ className }: GitHubConnectProps) {
  const { connected, github_login, loading, error, connect } =
    useGitHubConnection();

  if (loading) {
    return (
      <span
        className={`text-[var(--fg-muted)] text-xs ${className ?? ""}`}
      >
        Checking GitHub...
      </span>
    );
  }

  if (error) {
    return (
      <span
        className={`text-[var(--red)] text-xs ${className ?? ""}`}
        title={error}
      >
        GitHub error
      </span>
    );
  }

  if (connected && github_login) {
    return (
      <span
        className={`text-[var(--fg-muted)] text-xs ${className ?? ""}`}
      >
        <span className="text-[var(--green)]" aria-label="Connected">
          &bull;
        </span>{" "}
        @{github_login}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={connect}
      className={`text-xs px-2 py-1 rounded border border-[var(--border-default)] text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--bg-subtle)] transition-colors ${className ?? ""}`}
    >
      Connect GitHub
    </button>
  );
}

GitHubConnect.displayName = "GitHubConnect";

export { GitHubConnect };

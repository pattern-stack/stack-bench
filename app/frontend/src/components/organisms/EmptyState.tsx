/**
 * Empty state shown when the user has no stacks yet.
 *
 * Displayed after onboarding completes. Clean workspace landing
 * that shows connection status and available actions.
 */

import { useGitHubConnection } from "@/hooks/useGitHubConnection";

export function EmptyState() {
  const github = useGitHubConnection();

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] flex items-center justify-center p-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo + status */}
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] flex items-center justify-center mx-auto mb-5">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="12" width="14" height="3" rx="1" fill="var(--fg-subtle)" />
              <rect x="5" y="7" width="10" height="3" rx="1" fill="var(--fg-muted)" />
              <rect x="7" y="2" width="6" height="3" rx="1" fill="var(--accent)" />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-[var(--fg-default)] tracking-tight">
            No stacks yet
          </h1>
          <p className="mt-1.5 text-sm text-[var(--fg-muted)] leading-relaxed">
            Stacks will appear here once you push branches or import
            existing pull requests.
          </p>
        </div>

        {/* Status card */}
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] divide-y divide-[var(--border-muted)]">
          <StatusRow
            label="GitHub"
            value={
              github.connected ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)]" />
                  {github.githubLogin}
                </span>
              ) : (
                <span className="text-[var(--fg-subtle)]">Not connected</span>
              )
            }
          />
          <StatusRow
            label="Workspace"
            value={<span className="text-[var(--fg-subtle)]">Empty</span>}
          />
        </div>

        {/* Hint */}
        <p className="text-center text-xs text-[var(--fg-subtle)] leading-relaxed">
          Use{" "}
          <code className="font-[var(--font-mono)] text-[var(--accent)] bg-[var(--bg-surface)] px-1 py-0.5 rounded border border-[var(--border-muted)]">
            stack push
          </code>{" "}
          from your terminal to create your first stack.
        </p>
      </div>
    </div>
  );
}

function StatusRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-xs font-medium text-[var(--fg-muted)] uppercase tracking-wider">
        {label}
      </span>
      <span className="text-sm text-[var(--fg-default)]">{value}</span>
    </div>
  );
}

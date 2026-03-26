/**
 * Empty variant of StackSidebar shown when no stack data exists.
 *
 * Displays app branding, GitHub connection status, and placeholder
 * messages for the branch list and file tree zones.
 */

import { Icon } from "@/components/atoms";
import { useGitHubConnection } from "@/hooks/useGitHubConnection";

function StackSidebarEmpty() {
  const { connected, githubLogin } = useGitHubConnection();

  return (
    <aside className="flex flex-col h-full w-[var(--sidebar-width)] border-r border-[var(--border)] bg-[var(--bg-surface)]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--border-muted)]">
        <div className="flex items-center gap-2">
          <Icon name="git-branch" size="sm" className="text-[var(--fg-muted)]" />
          <span className="text-sm font-semibold text-[var(--fg-default)] tracking-tight">
            Stack Bench
          </span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-xs text-[var(--fg-muted)]">
          {connected ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)]" />
              <span>{githubLogin}</span>
            </>
          ) : (
            <span className="text-[var(--fg-subtle)]">GitHub not connected</span>
          )}
        </div>
      </div>

      {/* Branch list placeholder */}
      <div className="shrink-0 px-3 py-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] px-1">
          Stack
        </span>
        <div className="mt-2 flex items-center gap-2 px-1 py-2 text-sm text-[var(--fg-subtle)]">
          <Icon name="git-branch" size="xs" className="text-[var(--fg-subtle)]" />
          No branches
        </div>
      </div>

      {/* File tree placeholder */}
      <div className="flex-1 flex items-center justify-center min-h-0">
        <p className="text-xs text-[var(--fg-subtle)]">No files to show</p>
      </div>
    </aside>
  );
}

StackSidebarEmpty.displayName = "StackSidebarEmpty";

export { StackSidebarEmpty };

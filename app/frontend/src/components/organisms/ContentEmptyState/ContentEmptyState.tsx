/**
 * Content area empty state shown inside the AppShell when no stacks exist.
 *
 * Follows the EmptyState atom pattern (variant="no-data") with a
 * stacked-layers icon, heading, description, and CLI hint.
 */

function ContentEmptyState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="max-w-md w-full space-y-6 text-center px-8">
        {/* Stacked-layers icon */}
        <div className="w-12 h-12 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] flex items-center justify-center mx-auto">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect x="3" y="12" width="14" height="3" rx="1" fill="var(--fg-subtle)" />
            <rect x="5" y="7" width="10" height="3" rx="1" fill="var(--fg-muted)" />
            <rect x="7" y="2" width="6" height="3" rx="1" fill="var(--accent)" />
          </svg>
        </div>

        {/* Heading + description */}
        <div>
          <h1 className="text-lg font-semibold text-[var(--fg-default)] tracking-tight">
            No stacks yet
          </h1>
          <p className="mt-1.5 text-sm text-[var(--fg-muted)] leading-relaxed">
            Stacks will appear here once you push branches or import
            existing pull requests.
          </p>
        </div>

        {/* CLI hint */}
        <p className="text-xs text-[var(--fg-subtle)] leading-relaxed">
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

ContentEmptyState.displayName = "ContentEmptyState";

export { ContentEmptyState };

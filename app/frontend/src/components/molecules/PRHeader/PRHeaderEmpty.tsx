/**
 * Placeholder header shown when no branch is selected.
 *
 * Maintains the same height and border as the populated PRHeader
 * but shows only a muted title and subtitle.
 */

function PRHeaderEmpty() {
  return (
    <div className="px-6 py-3 bg-[var(--bg-surface)] border-b border-[var(--border)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg text-[var(--fg-muted)] leading-tight">
            Stack Bench
          </h2>
          <p className="mt-1 text-sm text-[var(--fg-subtle)]">
            Select a branch to view changes
          </p>
        </div>
      </div>
    </div>
  );
}

PRHeaderEmpty.displayName = "PRHeaderEmpty";

export { PRHeaderEmpty };

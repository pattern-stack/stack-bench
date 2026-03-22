import { ActivityLogEntry } from "@/components/molecules/ActivityLogEntry";
import type { ActivityLogEntry as ActivityLogEntryType } from "@/types/activity";

interface ActivityLogProps {
  entries: ActivityLogEntryType[];
  onClear?: () => void;
}

function ActivityLog({ entries, onClear }: ActivityLogProps) {
  return (
    <div className="flex flex-col border-t border-[var(--border-muted)]">
      {/* Section header */}
      <div className="flex items-center justify-between px-3 py-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
          Activity
        </span>
        {entries.length > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-[10px] text-[var(--fg-subtle)] hover:text-[var(--fg-muted)] transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Log entries */}
      <div className="overflow-y-auto max-h-36">
        {entries.length === 0 ? (
          <p className="text-xs text-[var(--fg-subtle)] px-3 py-2">
            No recent activity
          </p>
        ) : (
          entries.map((entry) => (
            <ActivityLogEntry key={entry.id} entry={entry} />
          ))
        )}
      </div>
    </div>
  );
}

ActivityLog.displayName = "ActivityLog";

export { ActivityLog };
export type { ActivityLogProps };

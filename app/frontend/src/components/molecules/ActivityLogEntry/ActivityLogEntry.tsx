import { Badge } from "@/components/atoms";
import { relativeTime } from "@/lib/time";
import type { ActivityLogEntry as ActivityLogEntryType } from "@/types/activity";
import type { BadgeProps } from "@/components/atoms";

interface ActivityLogEntryProps {
  entry: ActivityLogEntryType;
}

const operationColors: Record<ActivityLogEntryType["operation"], BadgeProps["color"]> = {
  sync: "accent",
  merge: "green",
  restack: "yellow",
  push: "purple",
};

function ActivityLogEntry({ entry }: ActivityLogEntryProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-1 min-w-0">
      <Badge size="sm" color={operationColors[entry.operation]} className="shrink-0">
        {entry.operation}
      </Badge>
      <span className="text-xs text-[var(--fg-muted)] truncate flex-1 min-w-0">
        {entry.description}
      </span>
      <span className="text-[10px] text-[var(--fg-subtle)] shrink-0">
        {relativeTime(entry.timestamp)}
      </span>
    </div>
  );
}

ActivityLogEntry.displayName = "ActivityLogEntry";

export { ActivityLogEntry };
export type { ActivityLogEntryProps };

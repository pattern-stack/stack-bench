import { cn } from "@/lib/utils";
import { StackDot } from "@/components/atoms";
import type { StackDotColor } from "@/components/atoms";
import { DiffStat } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface StackItemProps {
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  isActive?: boolean;
  isFirst?: boolean;
  isLast?: boolean;
  onClick?: () => void;
}

function getStackDotColor(status: string, isActive: boolean): StackDotColor {
  if (status === "merged") return "green";
  if (isActive) return "accent";
  return "default";
}

function StackItem({
  title,
  status,
  additions = 0,
  deletions = 0,
  isActive = false,
  isFirst = false,
  isLast = false,
  onClick,
}: StackItemProps) {
  const dotColor = getStackDotColor(status, isActive);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-stretch gap-3 w-full px-3 py-2.5 text-left transition-colors rounded-md",
        isActive
          ? "bg-[var(--accent-muted)] text-[var(--accent)]"
          : "text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]"
      )}
    >
      <StackDot color={dotColor} isFirst={isFirst} isLast={isLast} />
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <span
          className={cn(
            "text-sm font-medium truncate",
            isActive ? "text-[var(--accent)]" : "text-[var(--fg-default)]"
          )}
        >
          {title}
        </span>
        <div className="flex items-center gap-2">
          <StatusBadge status={status} />
          {(additions > 0 || deletions > 0) && (
            <DiffStat additions={additions} deletions={deletions} />
          )}
        </div>
      </div>
    </button>
  );
}

StackItem.displayName = "StackItem";

export { StackItem };
export type { StackItemProps };

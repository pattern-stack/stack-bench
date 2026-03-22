import { cn } from "@/lib/utils";
import { StackDot, DiffStat, CIDot, PRNumber, RestackBadge } from "@/components/atoms";
import type { StackDotColor } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { CIStatus } from "@/types/activity";

interface StackItemProps {
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  prNumber?: number | null;
  ciStatus?: CIStatus;
  needsRestack?: boolean;
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
  prNumber,
  ciStatus,
  needsRestack,
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
        "flex items-stretch gap-2 w-full px-3 py-1.5 text-left transition-colors rounded-md",
        isActive
          ? "bg-[var(--accent-muted)] text-[var(--accent)]"
          : "text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]"
      )}
    >
      <StackDot color={dotColor} isFirst={isFirst} isLast={isLast} />
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <span
          className={cn(
            "text-[13px] font-medium truncate",
            isActive ? "text-[var(--accent)]" : "text-[var(--fg-default)]"
          )}
        >
          {title}
        </span>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={status} />
          {prNumber != null && prNumber > 0 && <PRNumber number={prNumber} />}
          <CIDot status={ciStatus ?? "none"} />
          {needsRestack && <RestackBadge />}
          {(additions > 0 || deletions > 0) && (
            <span className="ml-auto">
              <DiffStat additions={additions} deletions={deletions} />
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

StackItem.displayName = "StackItem";

export { StackItem };
export type { StackItemProps };

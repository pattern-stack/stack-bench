import { cn } from "@/lib/utils";
import { MergeStepDot } from "@/components/atoms/MergeStepDot";
import { PRNumber } from "@/components/atoms/PRNumber";
import { BlockerBadge } from "@/components/atoms/BlockerBadge";
import type { MergeStepDotState } from "@/components/atoms/MergeStepDot";
import type { BlockerBadgeKind } from "@/components/atoms/BlockerBadge";
import type { MergeReadiness } from "@/types/merge-cascade";

const STEP_STATE_LABELS: Record<string, { label: string; className: string }> = {
  retargeting: { label: "Retargeting to trunk...", className: "text-[var(--yellow)]" },
  rebasing: { label: "Rebasing...", className: "text-[var(--yellow)]" },
  ci_pending: { label: "Waiting for CI...", className: "text-[var(--yellow)]" },
  completing: { label: "Completing merge...", className: "text-[var(--yellow)]" },
  merged: { label: "Merged", className: "text-[var(--green)]" },
  conflict: { label: "Conflict", className: "text-[var(--red)]" },
  failed: { label: "Failed", className: "text-[var(--red)]" },
  skipped: { label: "Skipped", className: "text-[var(--fg-subtle)] line-through" },
};

interface MergeStepItemProps {
  branchName: string;
  prNumber: number | null;
  position: number;
  readiness: MergeReadiness;
  stepState?: MergeStepDotState;
  stepError?: string | null;
  isTarget: boolean;
  onSetTarget?: () => void;
}

function MergeStepItem({
  branchName,
  prNumber,
  position,
  readiness,
  stepState,
  stepError,
  isTarget,
  onSetTarget,
}: MergeStepItemProps) {
  const isActive = !!stepState;
  const dotState: MergeStepDotState = stepState ?? (readiness.ready ? "pending" : "pending");
  const stateInfo = stepState ? STEP_STATE_LABELS[stepState] : undefined;

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
        !isActive && onSetTarget && "cursor-pointer hover:bg-[var(--bg-surface-hover)]",
        isTarget && "bg-[var(--accent-muted)]"
      )}
      onClick={!isActive ? onSetTarget : undefined}
    >
      <MergeStepDot state={dotState} />

      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span
          className={cn(
            "truncate font-[family-name:var(--font-mono)] text-xs",
            stepState === "skipped" ? "text-[var(--fg-subtle)] line-through" : "text-[var(--fg-default)]"
          )}
        >
          {position}. {branchName}
        </span>
        {prNumber != null && <PRNumber number={prNumber} />}
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        {isActive && stateInfo ? (
          <span className={cn("text-xs", stateInfo.className)}>
            {stateInfo.label}
          </span>
        ) : (
          <>
            {readiness.ready && (
              <span className="text-xs text-[var(--green)]">Ready</span>
            )}
            {readiness.blockers
              .filter((b) => b.kind !== "already_merged")
              .map((b) => (
                <BlockerBadge key={b.kind} kind={b.kind as BlockerBadgeKind} />
              ))}
          </>
        )}
      </div>

      {/* Error detail for failed/conflict */}
      {stepError && (stepState === "failed" || stepState === "conflict") && (
        <div className="w-full mt-1 text-xs text-[var(--red)]">{stepError}</div>
      )}
    </div>
  );
}

MergeStepItem.displayName = "MergeStepItem";

export { MergeStepItem };
export type { MergeStepItemProps };

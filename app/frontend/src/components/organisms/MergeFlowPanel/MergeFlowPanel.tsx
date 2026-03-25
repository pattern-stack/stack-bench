import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";
import { Button } from "@/components/atoms/Button";
import { MergeQueueList } from "@/components/molecules/MergeQueueList";
import { CascadeProgressBar } from "@/components/molecules/CascadeProgressBar";
import { MergeFlowSkeleton } from "./MergeFlowSkeleton";
import { useMergeCascade } from "@/hooks/useMergeCascade";
import { useMergeReadiness } from "@/hooks/useMergeReadiness";
import { shortBranch } from "@/lib/short-branch";
import type { BranchWithPR } from "@/types/stack";

interface MergeFlowPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stackId: string;
  branches: BranchWithPR[];
  onSyncTrunk?: () => void;
}

function MergeFlowPanel({
  isOpen,
  onClose,
  stackId,
  branches,
  onSyncTrunk,
}: MergeFlowPanelProps) {
  const [targetPosition, setTargetPosition] = useState<number | null>(null);
  const readinessMap = useMergeReadiness(branches);
  const {
    cascade,
    isActive,
    isPolling,
    startCascade,
    cancelCascade,
    reset,
    error,
  } = useMergeCascade(stackId);

  // Unmerged branches for queue display
  const unmergedBranches = useMemo(
    () =>
      branches.filter((b) => {
        const readiness = readinessMap.get(b.branch.id);
        return !readiness?.blockers.some((bl) => bl.kind === "already_merged");
      }),
    [branches, readinessMap]
  );

  // Check if all branches up to target have blockers
  const hasBlockers = useMemo(() => {
    const sorted = [...unmergedBranches].sort(
      (a, b) => a.branch.position - b.branch.position
    );
    const effectiveTarget =
      targetPosition ?? sorted[sorted.length - 1]?.branch.position ?? 1;

    return sorted
      .filter((b) => b.branch.position <= effectiveTarget)
      .some((b) => {
        const readiness = readinessMap.get(b.branch.id);
        return readiness && !readiness.ready;
      });
  }, [unmergedBranches, readinessMap, targetPosition]);

  // Derive the target branch name for the button label
  const targetBranchName = useMemo(() => {
    if (targetPosition == null) return null;
    const branch = unmergedBranches.find(
      (b) => b.branch.position === targetPosition
    );
    return branch ? shortBranch(branch.branch.name) : null;
  }, [targetPosition, unmergedBranches]);

  const cascadeState = cascade?.state;
  const isCompleted = cascadeState === "completed";
  const isFailed = cascadeState === "failed" || cascadeState === "cancelled";
  const hasError = !!error || (cascade?.error != null);
  const errorMessage = error ?? cascade?.error ?? null;

  // Conflict detection
  const conflictStep = cascade?.steps.find((s) => s.state === "conflict");

  const handleClose = () => {
    reset();
    setTargetPosition(null);
    onClose();
  };

  const handleMerge = () => {
    startCascade(targetPosition ?? undefined);
  };

  // Collapsed state — show a narrow toggle bar
  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={cn(
        "w-80 shrink-0 flex flex-col",
        "bg-[var(--bg-surface)] border-l border-[var(--border)]"
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--border)]">
        <Icon name="git-merge" size="sm" className="text-[var(--purple)]" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[var(--fg-default)]">
            Merge Stack
          </div>
        </div>
        <button
          onClick={handleClose}
          className="p-1 rounded hover:bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] hover:text-[var(--fg-default)] transition-colors"
        >
          <Icon name="x" size="sm" />
        </button>
      </div>

      {/* Progress bar — visible when cascade is active or terminal */}
      {cascade && (
        <div className="px-3 py-2 border-b border-[var(--border-muted)]">
          <CascadeProgressBar steps={cascade.steps} state={cascade.state} />
        </div>
      )}

      {/* Error banner */}
      {hasError && (
        <div className="px-3 py-2 bg-[var(--red-bg)] border-b border-[var(--red)]/20">
          <p className="text-xs text-[var(--red)]">
            {conflictStep
              ? `Conflict in ${shortBranch(conflictStep.branch_name)} \u2014 resolve locally and retry`
              : errorMessage}
          </p>
        </div>
      )}

      {/* Queue list */}
      <div className="flex-1 overflow-auto py-2">
        {isPolling && !cascade ? (
          <MergeFlowSkeleton />
        ) : (
          <MergeQueueList
            branches={branches}
            readinessMap={readinessMap}
            steps={cascade?.steps}
            targetPosition={targetPosition}
            onSetTarget={setTargetPosition}
          />
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2.5 border-t border-[var(--border)] flex items-center gap-2">
        {isCompleted ? (
          <>
            {onSyncTrunk && (
              <Button
                size="sm"
                variant="primary"
                onClick={onSyncTrunk}
                className="flex-1"
              >
                Sync trunk
              </Button>
            )}
            <Button size="sm" variant="subtle" onClick={handleClose}>
              Close
            </Button>
          </>
        ) : isActive ? (
          <Button
            size="sm"
            variant="subtle"
            onClick={cancelCascade}
            className="flex-1 !text-[var(--red)] !border-[var(--red)]/30 hover:!bg-[var(--red-bg)]"
          >
            Cancel cascade
          </Button>
        ) : isFailed ? (
          <Button size="sm" variant="subtle" onClick={handleClose} className="flex-1">
            Close
          </Button>
        ) : (
          <Button
            size="sm"
            variant="primary"
            onClick={handleMerge}
            disabled={hasBlockers || unmergedBranches.length === 0}
            className="flex-1"
          >
            {targetBranchName
              ? `Merge up to ${targetBranchName}`
              : "Merge all"}
          </Button>
        )}
      </div>
    </div>
  );
}

MergeFlowPanel.displayName = "MergeFlowPanel";

export { MergeFlowPanel };
export type { MergeFlowPanelProps };

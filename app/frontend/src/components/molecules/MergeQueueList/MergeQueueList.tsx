import { MergeStepItem } from "@/components/molecules/MergeStepItem";
import { shortBranch } from "@/lib/short-branch";
import type { BranchWithPR } from "@/types/stack";
import type { MergeReadiness, CascadeStepDetail } from "@/types/merge-cascade";

interface MergeQueueListProps {
  branches: BranchWithPR[];
  readinessMap: Map<string, MergeReadiness>;
  steps?: CascadeStepDetail[];
  targetPosition: number | null;
  onSetTarget: (position: number | null) => void;
}

const DEFAULT_READINESS: MergeReadiness = { ready: false, blockers: [] };

function MergeQueueList({
  branches,
  readinessMap,
  steps,
  targetPosition,
  onSetTarget,
}: MergeQueueListProps) {
  // Filter out already-merged branches
  const unmergedBranches = branches.filter((b) => {
    const readiness = readinessMap.get(b.branch.id);
    const isMerged = readiness?.blockers.some((bl) => bl.kind === "already_merged");
    return !isMerged;
  });

  // Sort by position (bottom-up, position 1 first)
  const sorted = [...unmergedBranches].sort(
    (a, b) => a.branch.position - b.branch.position
  );

  // Build a lookup from branch_id to cascade step
  const stepMap = new Map<string, CascadeStepDetail>();
  if (steps) {
    for (const step of steps) {
      stepMap.set(step.branch_id, step);
    }
  }

  const hasActiveSteps = !!steps && steps.length > 0;

  return (
    <div className="flex flex-col gap-0.5">
      {sorted.map((b) => {
        const readiness = readinessMap.get(b.branch.id) ?? DEFAULT_READINESS;
        const step = stepMap.get(b.branch.id);
        const position = b.branch.position;
        const effectiveTarget = targetPosition ?? sorted[sorted.length - 1]?.branch.position ?? 1;
        const isTarget = position === effectiveTarget;

        return (
          <MergeStepItem
            key={b.branch.id}
            branchName={shortBranch(b.branch.name)}
            prNumber={b.pull_request?.external_id ?? null}
            position={position}
            readiness={readiness}
            stepState={step?.state}
            stepError={step?.error}
            isTarget={isTarget}
            onSetTarget={
              hasActiveSteps
                ? undefined
                : () => onSetTarget(position === targetPosition ? null : position)
            }
          />
        );
      })}
    </div>
  );
}

MergeQueueList.displayName = "MergeQueueList";

export { MergeQueueList };
export type { MergeQueueListProps };

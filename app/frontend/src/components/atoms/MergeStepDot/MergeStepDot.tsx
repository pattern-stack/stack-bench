import { cn } from "@/lib/utils";

type MergeStepDotState =
  | "pending"
  | "retargeting"
  | "rebasing"
  | "ci_pending"
  | "completing"
  | "merged"
  | "conflict"
  | "failed"
  | "skipped";

interface MergeStepDotProps {
  state: MergeStepDotState;
}

const ACTIVE_STATES = new Set(["retargeting", "rebasing", "ci_pending", "completing"]);
const ERROR_STATES = new Set(["conflict", "failed"]);

function MergeStepDot({ state }: MergeStepDotProps) {
  const isActive = ACTIVE_STATES.has(state);
  const isError = ERROR_STATES.has(state);
  const isMerged = state === "merged";
  const isSkipped = state === "skipped";

  return (
    <span
      className={cn(
        "w-2 h-2 rounded-full inline-block shrink-0",
        isMerged && "bg-[var(--green)]",
        isActive && "bg-[var(--yellow)] animate-pulse",
        isError && "bg-[var(--red)]",
        isSkipped && "bg-[var(--fg-subtle)] opacity-50",
        state === "pending" && "bg-[var(--fg-subtle)]"
      )}
    />
  );
}

MergeStepDot.displayName = "MergeStepDot";

export { MergeStepDot };
export type { MergeStepDotProps, MergeStepDotState };

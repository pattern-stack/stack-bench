import { cn } from "@/lib/utils";
import type { CascadeState, CascadeStepDetail } from "@/types/merge-cascade";

interface CascadeProgressBarProps {
  steps: CascadeStepDetail[];
  state: CascadeState;
}

const SEGMENT_COLORS: Record<string, string> = {
  pending: "bg-[var(--fg-subtle)]",
  retargeting: "bg-[var(--yellow)]",
  rebasing: "bg-[var(--yellow)]",
  ci_pending: "bg-[var(--yellow)]",
  completing: "bg-[var(--yellow)]",
  merged: "bg-[var(--green)]",
  conflict: "bg-[var(--red)]",
  failed: "bg-[var(--red)]",
  skipped: "bg-[var(--fg-subtle)] opacity-50",
};

function CascadeProgressBar({ steps, state }: CascadeProgressBarProps) {
  const total = steps.length;
  const merged = steps.filter((s) => s.state === "merged").length;
  const failedStep = steps.find((s) => s.state === "failed" || s.state === "conflict");

  let label: string;
  let labelClass: string;

  if (state === "completed") {
    label = `All ${total} merged`;
    labelClass = "text-[var(--green)]";
  } else if (state === "failed" && failedStep) {
    label = `Failed at step ${failedStep.position} of ${total}`;
    labelClass = "text-[var(--red)]";
  } else if (state === "running") {
    label = `Merging ${merged + 1} of ${total}...`;
    labelClass = "text-[var(--fg-muted)]";
  } else if (state === "cancelled") {
    label = `Cancelled (${merged} of ${total} merged)`;
    labelClass = "text-[var(--fg-muted)]";
  } else {
    label = `${total} branches queued`;
    labelClass = "text-[var(--fg-muted)]";
  }

  return (
    <div className="space-y-1.5">
      <div className="text-xs font-medium">
        <span className={labelClass}>{label}</span>
      </div>
      <div
        className="grid gap-0.5 h-1.5 rounded-full overflow-hidden"
        style={{ gridTemplateColumns: `repeat(${total}, 1fr)` }}
      >
        {steps.map((step) => (
          <div
            key={step.id}
            className={cn(
              "rounded-full transition-colors",
              SEGMENT_COLORS[step.state] ?? "bg-[var(--fg-subtle)]"
            )}
          />
        ))}
      </div>
    </div>
  );
}

CascadeProgressBar.displayName = "CascadeProgressBar";

export { CascadeProgressBar };
export type { CascadeProgressBarProps };

import { cn } from "@/lib/utils";

interface BranchMetaProps {
  base: string;
  head: string;
  className?: string;
}

function BranchMeta({ base, head, className }: BranchMetaProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-xs text-[var(--fg-muted)]",
        className
      )}
    >
      <span>{base}</span>
      <span className="text-[var(--accent)]">&larr;</span>
      <span>{head}</span>
    </span>
  );
}

BranchMeta.displayName = "BranchMeta";

export { BranchMeta };
export type { BranchMetaProps };

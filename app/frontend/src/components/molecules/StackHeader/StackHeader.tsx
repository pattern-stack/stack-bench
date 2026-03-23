import { Icon, Button } from "@/components/atoms";
import type { StackSummary } from "@/types/activity";

interface StackHeaderProps {
  stackName: string;
  trunk: string;
  branchCount: number;
  summary: StackSummary;
  onSync?: () => void;
  onRestackAll?: () => void;
  onMerge?: () => void;
}

const summaryChips: {
  key: keyof Pick<StackSummary, "merged" | "open" | "draft" | "needsRestack">;
  label: (n: number) => string;
  color: string;
}[] = [
  { key: "merged", label: (n) => `${n} merged`, color: "var(--green)" },
  { key: "open", label: (n) => `${n} open`, color: "var(--accent)" },
  { key: "draft", label: (n) => `${n} draft`, color: "var(--fg-muted)" },
  {
    key: "needsRestack",
    label: (n) => `${n} need restack`,
    color: "var(--yellow)",
  },
];

function StackHeader({
  stackName,
  trunk,
  branchCount,
  summary,
  onSync,
  onRestackAll,
  onMerge,
}: StackHeaderProps) {
  return (
    <div className="flex flex-col gap-2 px-3 py-2 border-b border-[var(--border-muted)]">
      {/* Row 1: Name + branch count */}
      <div className="flex items-center gap-2">
        <Icon name="git-branch" size="sm" className="text-[var(--fg-muted)] shrink-0" />
        <span className="text-sm font-semibold text-[var(--fg-default)] truncate">
          {stackName}
        </span>
        <span className="text-xs text-[var(--fg-subtle)] shrink-0">
          {branchCount} {branchCount === 1 ? "branch" : "branches"}
        </span>
      </div>

      {/* Row 2: Status summary chips */}
      <div className="flex items-center gap-2 flex-wrap">
        {summaryChips.map(({ key, label, color }) => {
          const count = summary[key];
          if (count <= 0) return null;
          return (
            <span
              key={key}
              className="text-[11px] font-medium"
              style={{ color }}
            >
              {label(count)}
            </span>
          );
        })}
      </div>

      {/* Row 3: Toolbar buttons */}
      <div className="flex items-center gap-1.5">
        <Button variant="subtle" size="sm" onClick={onSync} title={`Sync ${trunk}`}>
          <Icon name="download-cloud" size="xs" />
          Sync
        </Button>
        <Button
          variant="subtle"
          size="sm"
          onClick={onRestackAll}
          disabled={summary.needsRestack === 0}
        >
          <Icon name="refresh-cw" size="xs" />
          Restack ({summary.needsRestack})
        </Button>
        <Button variant="subtle" size="sm" onClick={onMerge}>
          <Icon name="git-merge" size="xs" />
          Merge
        </Button>
      </div>
    </div>
  );
}

StackHeader.displayName = "StackHeader";

export { StackHeader };
export type { StackHeaderProps };

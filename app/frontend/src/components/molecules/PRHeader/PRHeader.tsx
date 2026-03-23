import { BranchMeta } from "@/components/atoms/BranchMeta";
import { DiffStat } from "@/components/atoms/DiffStat";
import { Button, Icon } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";

interface PRHeaderProps {
  title: string;
  baseBranch: string;
  headBranch: string;
  description?: string | null;
  status?: string;
  fileCount?: number;
  additions?: number;
  deletions?: number;
  onPush?: () => void;
  onRestack?: () => void;
  onCollapseAll?: () => void;
  onExpandAll?: () => void;
  floatingComments?: boolean;
  onToggleCommentMode?: () => void;
}

function PRHeader({
  title, baseBranch, headBranch, description, status,
  fileCount, additions, deletions,
  onPush, onRestack, onCollapseAll, onExpandAll,
  floatingComments, onToggleCommentMode,
}: PRHeaderProps) {
  return (
    <div className="px-6 py-3 bg-[var(--bg-surface)] border-b border-[var(--border)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-[var(--fg-default)] leading-tight">
            {title}
          </h2>
          <div className="mt-1 flex items-center gap-3">
            <BranchMeta base={baseBranch} head={headBranch} />
            {status && <StatusBadge status={status} />}
          </div>
          {description && (
            <p className="mt-1.5 text-sm text-[var(--fg-muted)] leading-normal">
              {description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 pt-0.5">
          <Button
            variant="subtle"
            size="sm"
            onClick={onRestack}
            disabled={!onRestack}
          >
            <Icon name="refresh-cw" size="xs" />
            Restack downstream
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onPush}
            disabled={!onPush}
          >
            Mark ready &amp; push
          </Button>
        </div>
      </div>
      {fileCount != null && fileCount > 0 && (
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-[var(--fg-muted)]">
            {fileCount} changed {fileCount === 1 ? "file" : "files"}
            {additions != null && deletions != null && (
              <>
                {" "}
                <DiffStat additions={additions} deletions={deletions} />
              </>
            )}
          </span>
          <div className="flex items-center gap-1">
            {onToggleCommentMode && (
              <Button variant="subtle" size="sm" onClick={onToggleCommentMode}>
                <Icon name={floatingComments ? "message-square" : "layout"} size="xs" />
                {floatingComments ? "Floating" : "Inline"}
              </Button>
            )}
            <Button variant="subtle" size="sm" onClick={onExpandAll}>
              <Icon name="chevrons-down" size="xs" />
              Expand all
            </Button>
            <Button variant="subtle" size="sm" onClick={onCollapseAll}>
              <Icon name="chevrons-up" size="xs" />
              Collapse all
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

PRHeader.displayName = "PRHeader";

export { PRHeader };
export type { PRHeaderProps };

import { FileIcon } from "@/components/atoms/FileIcon";
import { IndentGuide } from "@/components/atoms/IndentGuide";
import { DiffBadge } from "@/components/atoms/DiffBadge";
import { DiffStat } from "@/components/atoms/DiffStat";
import { cn } from "@/lib/utils";
import type { DiffFile } from "@/types/diff";

type ChangeType = DiffFile["change_type"];

interface FileTreeItemProps {
  name: string;
  type: "file" | "dir";
  depth: number;
  isOpen?: boolean;
  isActive?: boolean;
  highlight?: string;
  changeType?: ChangeType;
  additions?: number;
  deletions?: number;
  hasDirtyChildren?: boolean;
  onClick: () => void;
}

function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-[var(--accent-muted)] text-inherit rounded-sm px-px">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

const changeTypeColor: Record<ChangeType, string> = {
  added: "text-[var(--green)]",
  modified: "text-[var(--yellow)]",
  deleted: "text-[var(--red)] line-through",
  renamed: "text-[var(--purple)]",
};

function FileTreeItem({
  name,
  type,
  depth,
  isOpen = false,
  isActive = false,
  highlight,
  changeType,
  additions,
  deletions,
  hasDirtyChildren = false,
  onClick,
}: FileTreeItemProps) {
  const nameColor = isActive
    ? "text-[var(--accent)]"
    : changeType
      ? changeTypeColor[changeType]
      : "text-[var(--fg-default)]";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex items-center w-full gap-1.5 py-0.5 pr-2 text-sm text-left rounded group",
        "text-[13px]",
        "hover:bg-[var(--bg-surface-hover)] transition-colors",
        isActive && "bg-[var(--accent-muted)]",
        !isActive && !changeType && "text-[var(--fg-default)]"
      )}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <IndentGuide depth={depth} />
      <FileIcon type={type} isOpen={isOpen} fileName={name} />
      <span className={cn("truncate flex-1 min-w-0", nameColor)}>
        {highlight ? highlightMatch(name, highlight) : name}
      </span>
      {hasDirtyChildren && !changeType && (
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--yellow)] opacity-60 shrink-0" />
      )}
      {changeType && (
        <span className="flex items-center gap-1 shrink-0">
          <DiffBadge changeType={changeType} />
          {(additions != null || deletions != null) && (
            <DiffStat additions={additions ?? 0} deletions={deletions ?? 0} />
          )}
        </span>
      )}
    </button>
  );
}

FileTreeItem.displayName = "FileTreeItem";

export { FileTreeItem };
export type { FileTreeItemProps, ChangeType };

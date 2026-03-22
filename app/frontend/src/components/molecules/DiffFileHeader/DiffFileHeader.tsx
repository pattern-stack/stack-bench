import { DiffBadge } from "@/components/atoms/DiffBadge";
import { DiffStat } from "@/components/atoms/DiffStat";
import { Icon } from "@/components/atoms/Icon";
import type { DiffFile } from "@/types/diff";

interface DiffFileHeaderProps {
  file: DiffFile;
  expanded: boolean;
  onToggle: () => void;
}

/** Split path into directory (dimmed) and filename (bright). */
function splitPath(path: string): { dir: string; name: string } {
  const lastSlash = path.lastIndexOf("/");
  if (lastSlash === -1) {
    return { dir: "", name: path };
  }
  return {
    dir: path.slice(0, lastSlash + 1),
    name: path.slice(lastSlash + 1),
  };
}

function DiffFileHeader({ file, expanded, onToggle }: DiffFileHeaderProps) {
  const { dir, name } = splitPath(file.path);

  return (
    <button
      type="button"
      onClick={onToggle}
      className="sticky top-0 z-10 flex items-center gap-2 w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border)] rounded-t text-left hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer"
    >
      <Icon
        name={expanded ? "chevron-down" : "chevron-right"}
        size="sm"
        className="text-[var(--fg-muted)] shrink-0"
      />

      <DiffBadge changeType={file.change_type} />

      <span className="font-[family-name:var(--font-mono)] text-xs truncate min-w-0">
        <span className="text-[var(--fg-muted)]">{dir}</span>
        <span className="text-[var(--fg-default)] font-medium">{name}</span>
      </span>

      <span className="ml-auto shrink-0">
        <DiffStat additions={file.additions} deletions={file.deletions} />
      </span>
    </button>
  );
}

DiffFileHeader.displayName = "DiffFileHeader";

export { DiffFileHeader };
export type { DiffFileHeaderProps };

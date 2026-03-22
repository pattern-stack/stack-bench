import { Checkbox } from "@/components/atoms/Checkbox";
import { DiffBadge } from "@/components/atoms/DiffBadge";
import { DiffStat } from "@/components/atoms/DiffStat";
import { FileIcon } from "@/components/atoms/FileIcon";
import { Icon } from "@/components/atoms/Icon";
import type { DiffFile } from "@/types/diff";

interface DiffFileHeaderProps {
  file: DiffFile;
  expanded: boolean;
  viewed?: boolean;
  onToggle: () => void;
  onViewedChange?: (viewed: boolean) => void;
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

function DiffFileHeader({ file, expanded, viewed = false, onToggle, onViewedChange }: DiffFileHeaderProps) {
  const { dir, name } = splitPath(file.path);

  return (
    <div
      className="sticky top-0 z-10 flex items-center gap-2 w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border)] rounded-t hover:bg-[var(--bg-surface-hover)] transition-colors"
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-2 min-w-0 flex-1 text-left cursor-pointer"
      >
        <Icon
          name={expanded ? "chevron-down" : "chevron-right"}
          size="sm"
          className="text-[var(--fg-muted)] shrink-0"
        />

        <DiffBadge changeType={file.change_type} />

        <FileIcon type="file" fileName={name} />

        <span className="font-[family-name:var(--font-mono)] text-xs truncate min-w-0">
          <span className="text-[var(--fg-muted)]">{dir}</span>
          <span className="text-[var(--fg-default)] font-medium">{name}</span>
        </span>
      </button>

      <span className="shrink-0">
        <DiffStat additions={file.additions} deletions={file.deletions} />
      </span>

      {onViewedChange && (
        <span className="shrink-0 ml-2" onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={viewed}
            onChange={onViewedChange}
            label="Viewed"
          />
        </span>
      )}
    </div>
  );
}

DiffFileHeader.displayName = "DiffFileHeader";

export { DiffFileHeader };
export type { DiffFileHeaderProps };

import { FileIcon } from "@/components/atoms/FileIcon";
import { DiffBadge } from "@/components/atoms/DiffBadge";
import { DiffStat } from "@/components/atoms/DiffStat";
import { cn } from "@/lib/utils";
import type { DiffFile } from "@/types/diff";

export interface DiffFileListItem {
  path: string;
  fileName: string;
  changeType: DiffFile["change_type"];
  additions: number;
  deletions: number;
}

interface DiffFileListProps {
  files: DiffFileListItem[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function DiffFileList({ files, selectedPath, onSelectFile }: DiffFileListProps) {
  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[var(--fg-muted)] text-xs">No changed files</p>
      </div>
    );
  }

  return (
    <div className="py-1">
      {files.map((file) => {
        const isActive = selectedPath === file.path;
        const dirPart = file.path.includes("/")
          ? file.path.slice(0, file.path.lastIndexOf("/") + 1)
          : "";

        return (
          <button
            key={file.path}
            type="button"
            onClick={() => onSelectFile(file.path)}
            className={cn(
              "w-full flex items-center gap-2 px-3 py-1 text-left text-xs transition-colors",
              "hover:bg-[var(--bg-surface-hover)]",
              isActive && "bg-[var(--accent-muted)] text-[var(--accent)]"
            )}
          >
            <FileIcon type="file" fileName={file.fileName} className="shrink-0" />
            <span className="flex-1 min-w-0 truncate font-[family-name:var(--font-mono)]">
              {dirPart && (
                <span className="text-[var(--fg-subtle)]">{dirPart}</span>
              )}
              <span className={cn(isActive ? "text-[var(--accent)]" : "text-[var(--fg-default)]")}>
                {file.fileName}
              </span>
            </span>
            <DiffBadge changeType={file.changeType} />
            <DiffStat additions={file.additions} deletions={file.deletions} />
          </button>
        );
      })}
    </div>
  );
}

DiffFileList.displayName = "DiffFileList";

export { DiffFileList };
export type { DiffFileListProps };

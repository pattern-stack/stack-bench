import { FileTreeItem } from "@/components/molecules/FileTreeItem";
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
      {files.map((file) => (
        <FileTreeItem
          key={file.path}
          name={file.fileName}
          type="file"
          depth={0}
          isActive={selectedPath === file.path}
          changeType={file.changeType}
          additions={file.additions}
          deletions={file.deletions}
          onClick={() => onSelectFile(file.path)}
        />
      ))}
    </div>
  );
}

DiffFileList.displayName = "DiffFileList";

export { DiffFileList };
export type { DiffFileListProps };

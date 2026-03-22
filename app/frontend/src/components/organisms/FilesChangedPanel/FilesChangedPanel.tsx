import { FileListSummary } from "@/components/molecules/FileListSummary";
import { DiffFileMolecule } from "@/components/molecules/DiffFile";
import type { DiffData } from "@/types/diff";

interface FilesChangedPanelProps {
  diffData: DiffData;
}

function FilesChangedPanel({ diffData }: FilesChangedPanelProps) {
  if (diffData.files.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[var(--fg-muted)] text-sm">No files changed</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <FileListSummary
        fileCount={diffData.files.length}
        additions={diffData.total_additions}
        deletions={diffData.total_deletions}
      />
      {diffData.files.map((file) => (
        <DiffFileMolecule key={file.path} file={file} />
      ))}
    </div>
  );
}

FilesChangedPanel.displayName = "FilesChangedPanel";

export { FilesChangedPanel };
export type { FilesChangedPanelProps };

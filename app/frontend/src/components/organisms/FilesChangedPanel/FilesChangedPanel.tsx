import { useState, useCallback } from "react";
import { FileListSummary } from "@/components/molecules/FileListSummary";
import { DiffFileMolecule } from "@/components/molecules/DiffFile";
import type { DiffData } from "@/types/diff";

interface FilesChangedPanelProps {
  diffData: DiffData;
}

function FilesChangedPanel({ diffData }: FilesChangedPanelProps) {
  const [viewedFiles, setViewedFiles] = useState<Set<string>>(new Set());

  const handleViewedChange = useCallback((path: string, viewed: boolean) => {
    setViewedFiles((prev) => {
      const next = new Set(prev);
      if (viewed) next.add(path);
      else next.delete(path);
      return next;
    });
  }, []);

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
        <DiffFileMolecule
          key={file.path}
          file={file}
          viewed={viewedFiles.has(file.path)}
          onViewedChange={(v) => handleViewedChange(file.path, v)}
        />
      ))}
    </div>
  );
}

FilesChangedPanel.displayName = "FilesChangedPanel";

export { FilesChangedPanel };
export type { FilesChangedPanelProps };

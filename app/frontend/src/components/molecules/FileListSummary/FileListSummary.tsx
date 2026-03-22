interface FileListSummaryProps {
  fileCount: number;
  additions: number;
  deletions: number;
  selectedCount?: number;
}

function FileListSummary({ fileCount, additions, deletions, selectedCount = 0 }: FileListSummaryProps) {
  return (
    <p className="text-xs text-[var(--fg-muted)] px-4 py-3">
      Showing{" "}
      <span className="text-[var(--fg-default)] font-medium">
        {fileCount} changed {fileCount === 1 ? "file" : "files"}
      </span>
      {" "}with{" "}
      <span className="text-[var(--green)] font-medium">+{additions}</span>
      {" "}and{" "}
      <span className="text-[var(--red)] font-medium">-{deletions}</span>
      {selectedCount > 0 && (
        <>
          {" "}&middot;{" "}
          <span className="text-[var(--accent-emerald)] font-medium">
            {selectedCount} {selectedCount === 1 ? "line" : "lines"} selected
          </span>
        </>
      )}
    </p>
  );
}

FileListSummary.displayName = "FileListSummary";

export { FileListSummary };
export type { FileListSummaryProps };

import { useState } from "react";
import { FileTree } from "@/components/organisms/FileTree";
import { FileContent } from "@/components/molecules/FileContent";
import { PathBar } from "@/components/molecules/PathBar";
import { useFileTree } from "@/hooks/useFileTree";
import { useFileContent } from "@/hooks/useFileContent";

interface FileViewerPanelProps {
  stackId?: string;
  branchId?: string;
}

function FileViewerPanel({ stackId, branchId }: FileViewerPanelProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const { data: tree } = useFileTree(stackId, branchId);
  const { data: fileContent } = useFileContent(stackId, branchId, selectedPath);

  if (!tree) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[var(--fg-muted)] text-sm">Loading file tree...</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* File tree sidebar */}
      <div className="w-[250px] shrink-0 border-r border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden flex flex-col">
        <FileTree
          tree={tree}
          selectedPath={selectedPath}
          onSelectFile={setSelectedPath}
        />
      </div>

      {/* File content area */}
      <div className="flex-1 min-w-0 overflow-hidden flex flex-col">
        {fileContent ? (
          <>
            <PathBar path={fileContent.path} />
            <div className="flex-1 min-h-0 overflow-hidden">
              <FileContent file={fileContent} />
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[var(--fg-muted)] text-sm">
              {selectedPath
                ? "File not available"
                : "Select a file to view its contents"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

FileViewerPanel.displayName = "FileViewerPanel";

export { FileViewerPanel };
export type { FileViewerPanelProps };

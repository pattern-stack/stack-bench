import { useState, useEffect } from "react";
import { AppShell } from "@/components/templates";
import { FilesChangedPanel } from "@/components/organisms/FilesChangedPanel";
import { FileContent } from "@/components/molecules/FileContent";
import { PathBar } from "@/components/molecules/PathBar";
import { useStackDetail } from "@/hooks/useStackDetail";
import { useBranchDiff } from "@/hooks/useBranchDiff";
import { useFileTree } from "@/hooks/useFileTree";
import { useFileContent } from "@/hooks/useFileContent";
import type { StackConnectorItem } from "@/components/molecules";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { SidebarMode } from "@/types/sidebar";

function branchTitle(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

const mockDiffStats: Record<string, { additions: number; deletions: number }> = {
  "b-001": { additions: 48, deletions: 12 },
  "b-002": { additions: 156, deletions: 23 },
  "b-003": { additions: 89, deletions: 34 },
  "b-004": { additions: 0, deletions: 0 },
};

export function App() {
  const { data, loading, error } = useStackDetail();
  const [activeIndex, setActiveIndex] = useState(2);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("diffs");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);

  // TODO: Lift selectedLineCount from FilesChangedPanel in a future PR
  const selectedLineCount = 0;

  const activeBranchId = data?.branches[activeIndex]?.branch.id;
  const { data: diffData } = useBranchDiff(activeBranchId);
  const { data: fileTree } = useFileTree(activeBranchId);
  const { data: fileContent } = useFileContent(activeBranchId, sidebarMode === "files" ? selectedPath : null);

  // Reset sidebar mode and selection when branch changes
  useEffect(() => {
    setSidebarMode("diffs");
    setSelectedPath(null);
  }, [activeIndex]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--fg-muted)] text-sm">Loading...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] flex items-center justify-center">
        <p className="text-[var(--red)] text-sm">{error ?? "No data"}</p>
      </div>
    );
  }

  const items: StackConnectorItem[] = data.branches.map((b) => {
    const displayStatus = b.pull_request?.state ?? b.branch.state;
    const stats = mockDiffStats[b.branch.id] ?? { additions: 0, deletions: 0 };

    return {
      id: b.branch.id,
      title: branchTitle(b.branch.name),
      status: displayStatus,
      additions: stats.additions,
      deletions: stats.deletions,
    };
  });

  const activeBranch = data.branches[activeIndex] ?? null;

  // Derive DiffFileListItem[] from diff data
  const diffFiles: DiffFileListItem[] = (diffData?.files ?? []).map((f) => {
    const fileName = f.path.includes("/")
      ? f.path.slice(f.path.lastIndexOf("/") + 1)
      : f.path;
    return {
      path: f.path,
      fileName,
      changeType: f.change_type,
      additions: f.additions,
      deletions: f.deletions,
    };
  });

  const fileCount = diffData?.files.length ?? 0;

  return (
    <AppShell
      stackName={data.stack.name}
      trunk={data.stack.trunk}
      items={items}
      activeIndex={activeIndex}
      onSelect={setActiveIndex}
      activeBranch={activeBranch}
      agentOpen={agentOpen}
      onAgentToggle={() => setAgentOpen((prev) => !prev)}
      selectedLineCount={selectedLineCount}
      sidebarMode={sidebarMode}
      onSidebarModeChange={setSidebarMode}
      diffFiles={diffFiles}
      fileTree={fileTree}
      selectedPath={selectedPath}
      onSelectFile={setSelectedPath}
      diffFileCount={fileCount}
    >
      {sidebarMode === "diffs" && (
        diffData ? (
          <FilesChangedPanel diffData={diffData} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[var(--fg-muted)] text-sm">Select a branch to view changes</p>
          </div>
        )
      )}
      {sidebarMode === "files" && (
        fileContent ? (
          <>
            <PathBar path={fileContent.path} />
            <div className="flex-1 min-h-0 overflow-hidden">
              <FileContent file={fileContent} />
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[var(--fg-muted)] text-sm">
              {selectedPath ? "File not available" : "Select a file to view its contents"}
            </p>
          </div>
        )
      )}
    </AppShell>
  );
}

import { useState, useEffect, useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { AppShell } from "@/components/templates";
import { FilesChangedPanel } from "@/components/organisms/FilesChangedPanel";
import { FileContent } from "@/components/molecules/FileContent";
import { PathBar } from "@/components/molecules/PathBar";
import { useStackDetail } from "@/hooks/useStackDetail";
import { useStackList } from "@/hooks/useStackList";
import { useBranchDiff, branchDiffKeys } from "@/hooks/useBranchDiff";
import { useFileTree } from "@/hooks/useFileTree";
import { useFileContent } from "@/hooks/useFileContent";
import { mockActivityEntries } from "@/lib/mock-activity-data";
import type { StackConnectorItem } from "@/components/molecules";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";
import type { DiffData } from "@/types/diff";
import type { SidebarMode } from "@/types/sidebar";
import type { CIStatus, StackSummary, ActivityLogEntry } from "@/types/activity";

function branchTitle(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}


/** Status values that count as "draft" (no PR or local-only) */
const DRAFT_STATUSES = new Set(["draft", "created", "local"]);
/** Status values that count as "open" (has a PR, under review) */
const OPEN_STATUSES = new Set(["open", "reviewing", "review", "approved", "ready"]);

function computeSummary(items: StackConnectorItem[]): StackSummary {
  let merged = 0;
  let open = 0;
  let draft = 0;
  let needsRestack = 0;

  for (const item of items) {
    if (item.status === "merged") merged++;
    else if (OPEN_STATUSES.has(item.status)) open++;
    else if (DRAFT_STATUSES.has(item.status)) draft++;
    if (item.needsRestack) needsRestack++;
  }

  return { branchCount: items.length, merged, open, draft, needsRestack };
}

export function App() {
  const [selectedStackId, setSelectedStackId] = useState<string | undefined>(undefined);
  const { data, loading, error } = useStackDetail(selectedStackId);
  const [activeIndex, setActiveIndex] = useState(0);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("diffs");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [activityEntries, setActivityEntries] = useState<ActivityLogEntry[]>(mockActivityEntries);
  const [forceExpanded, setForceExpanded] = useState<boolean | null>(null);

  // TODO: Lift selectedLineCount from FilesChangedPanel in a future PR
  const selectedLineCount = 0;

  const stackId = data?.stack.id;
  const activeBranchId = data?.branches[activeIndex]?.branch.id;
  const { data: diffData } = useBranchDiff(stackId, activeBranchId);
  const { data: fileTree } = useFileTree(stackId, activeBranchId);
  const { data: fileContent } = useFileContent(stackId, activeBranchId, sidebarMode === "files" ? selectedPath : null);

  // Fetch all stacks for the same project (for the stack switcher)
  const projectId = data?.stack.project_id;
  const { data: stacks } = useStackList(projectId);

  const handleStackChange = (id: string) => {
    setSelectedStackId(id);
    setActiveIndex(0);
    setSidebarMode("diffs");
    setSelectedPath(null);
    setForceExpanded(null);
  };

  // Subscribe reactively to all branch diffs
  const branchDiffQueries = useQueries({
    queries: (data?.branches ?? []).map((b) => ({
      queryKey: branchDiffKeys.diff(stackId ?? "", b.branch.id),
      queryFn: () => apiClient.get<DiffData>(`/api/v1/stacks/${stackId}/branches/${b.branch.id}/diff`),
      enabled: !!stackId,
      staleTime: Infinity,
    })),
  });

  // Reset sidebar mode and selection when branch changes
  useEffect(() => {
    setSidebarMode("diffs");
    setSelectedPath(null);
    setForceExpanded(null);
  }, [activeIndex]);

  // Build changed files map for dirty state in file explorer
  const changedFiles = useMemo(() => {
    if (!diffData) return undefined;
    const map = new Map<string, ChangedFileInfo>();
    for (const f of diffData.files) {
      map.set(f.path, {
        changeType: f.change_type,
        additions: f.additions,
        deletions: f.deletions,
      });
    }
    return map;
  }, [diffData]);

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

  const items: StackConnectorItem[] = data.branches.map((b, index) => {
    const displayStatus = b.pull_request?.state ?? b.branch.state;
    const diffResult = branchDiffQueries[index]?.data;

    return {
      id: b.branch.id,
      title: branchTitle(b.branch.name),
      status: displayStatus,
      additions: diffResult?.total_additions,
      deletions: diffResult?.total_deletions,
      prNumber: b.pull_request?.external_id ?? null,
      ciStatus: "none" as CIStatus,
      needsRestack: false,
    };
  });

  const summary = computeSummary(items);
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
      stacks={stacks}
      onStackChange={handleStackChange}
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
      changedFiles={changedFiles}
      summary={summary}
      activityEntries={activityEntries}
      onSync={() => console.log("sync trunk")}
      onMerge={async () => {
        if (!stackId) return;
        try {
          const result = await apiClient.post<{ stack_id: string; merged: { branch: string; pr_number: number; merged: boolean }[] }>(`/api/v1/stacks/${stackId}/merge`);
          const count = result.merged.length;
          setActivityEntries((prev) => [
            { id: crypto.randomUUID(), operation: "merge", description: `Merged ${count} PR${count !== 1 ? "s" : ""} in stack`, timestamp: new Date().toISOString() },
            ...prev,
          ]);
        } catch (err) {
          const desc = err instanceof Error ? err.message : "Merge failed";
          setActivityEntries((prev) => [
            { id: crypto.randomUUID(), operation: "merge", description: desc, timestamp: new Date().toISOString() },
            ...prev,
          ]);
        }
      }}
      onClearActivity={() => setActivityEntries([])}
      fileCount={diffData?.files.length}
      additions={diffData?.total_additions}
      deletions={diffData?.total_deletions}
      onCollapseAll={() => setForceExpanded(false)}
      onExpandAll={() => setForceExpanded(true)}
    >
      {sidebarMode === "diffs" && (
        diffData ? (
          <FilesChangedPanel diffData={diffData} forceExpanded={forceExpanded} />
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

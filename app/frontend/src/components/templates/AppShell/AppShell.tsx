import type { ReactNode } from "react";
import { StackSidebar } from "@/components/organisms/StackSidebar";
import { StackSidebarEmpty } from "@/components/organisms/StackSidebar/StackSidebarEmpty";
import { AgentPanel } from "@/components/organisms/AgentPanel";
import { MergeFlowPanel } from "@/components/organisms/MergeFlowPanel";
import { PRHeader } from "@/components/molecules/PRHeader";
import { PRHeaderEmpty } from "@/components/molecules/PRHeader/PRHeaderEmpty";
import { HeaderSkeleton } from "@/components/molecules/PRHeader/HeaderSkeleton";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { BranchWithPR, Stack } from "@/types/stack";
import type { SidebarMode } from "@/types/sidebar";
import type { FileTreeNode } from "@/types/file-tree";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";
import type { StackSummary, ActivityLogEntry } from "@/types/activity";

interface AppShellProps {
  // Data props — optional for empty mode (detected via !stackName)
  stackName?: string;
  trunk?: string;
  items?: StackConnectorItem[];
  activeIndex?: number;
  onSelect?: (index: number) => void;
  activeBranch?: BranchWithPR | null;
  selectedLineCount?: number;

  // Layout/interaction — always required
  agentOpen: boolean;
  onAgentToggle: () => void;
  children?: ReactNode;

  // Sidebar props — optional for empty mode
  sidebarMode?: SidebarMode;
  onSidebarModeChange?: (mode: SidebarMode) => void;
  diffFiles?: DiffFileListItem[];
  fileTree?: FileTreeNode | null;
  selectedPath?: string | null;
  onSelectFile?: (path: string) => void;
  diffFileCount?: number;
  onRefresh?: () => void;
  changedFiles?: Map<string, ChangedFileInfo>;

  // Stack header + activity props
  summary?: StackSummary;
  activityEntries?: ActivityLogEntry[];
  onSync?: () => void;
  onMerge?: () => void;
  onClearActivity?: () => void;

  // Stack switcher props
  stacks?: Stack[];
  onStackChange?: (id: string) => void;

  // Merge panel props
  mergeOpen?: boolean;
  onMergeClose?: () => void;
  stackId?: string;
  branches?: BranchWithPR[];

  // Diff toolbar props
  fileCount?: number;
  additions?: number;
  deletions?: number;
  onCollapseAll?: () => void;
  onExpandAll?: () => void;
  floatingComments?: boolean;
  onToggleCommentMode?: () => void;
  diffLoading?: boolean;
  treeLoading?: boolean;
}

import { shortBranch } from "@/lib/short-branch";

function AppShell({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
  activeBranch,
  agentOpen,
  onAgentToggle,
  selectedLineCount,
  children,
  sidebarMode,
  onSidebarModeChange,
  diffFiles,
  fileTree,
  selectedPath,
  onSelectFile,
  diffFileCount,
  onRefresh,
  changedFiles,
  stacks,
  onStackChange,
  summary,
  activityEntries,
  onSync,
  onMerge,
  onClearActivity,
  mergeOpen,
  onMergeClose,
  stackId,
  branches,
  fileCount,
  additions,
  deletions,
  onCollapseAll,
  onExpandAll,
  floatingComments,
  onToggleCommentMode,
  diffLoading,
  treeLoading,
}: AppShellProps) {
  // Derive PRHeader props from the active branch (only used in populated mode)
  const pr = activeBranch?.pull_request;
  const branchName = activeBranch?.branch.name ?? "";
  const title = pr?.title ?? shortBranch(branchName);
  const description = pr?.description ?? (pr ? null : "No pull request");
  const headBranch = shortBranch(branchName);

  // Full branch names for tooltips
  const fullHeadBranch = activeBranch?.branch.name ?? "";

  // Base branch: for position 1, base is trunk. For others, it's the previous branch.
  const position = activeBranch?.branch.position ?? 1;
  const baseBranch = position <= 1 ? (trunk ?? "") : shortBranch(
    items?.[( activeIndex ?? 0) - 1]?.title ?? (trunk ?? "")
  );

  // Display status: prefer PR state over branch state
  const displayStatus = pr?.state ?? activeBranch?.branch.state ?? "created";

  const isEmpty = !stackName;

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      {isEmpty ? (
        <StackSidebarEmpty />
      ) : (
        <StackSidebar
          stackName={stackName}
          trunk={trunk!}
          stacks={stacks}
          onStackChange={onStackChange}
          items={items!}
          activeIndex={activeIndex!}
          onSelect={onSelect!}
          summary={summary!}
          activityEntries={activityEntries!}
          onSync={onSync}
          onRestackAll={summary!.needsRestack > 0 ? () => console.log("restack all") : undefined}
          onMerge={onMerge}
          onClearActivity={onClearActivity}
          sidebarMode={sidebarMode!}
          onSidebarModeChange={onSidebarModeChange!}
          diffFiles={diffFiles!}
          fileTree={fileTree ?? null}
          selectedPath={selectedPath ?? null}
          onSelectFile={onSelectFile!}
          diffFileCount={diffFileCount}
          onRefresh={onRefresh}
          changedFiles={changedFiles}
          diffLoading={diffLoading}
          treeLoading={treeLoading}
        />
      )}
      <main className="flex-1 flex flex-col min-w-0">
        {isEmpty ? (
          <PRHeaderEmpty />
        ) : diffLoading ? (
          <HeaderSkeleton />
        ) : (
          <PRHeader
            title={title}
            baseBranch={baseBranch}
            headBranch={headBranch}
            fullHeadBranch={fullHeadBranch}
            description={description}
            status={displayStatus}
            fileCount={fileCount}
            additions={additions}
            deletions={deletions}
            onCollapseAll={onCollapseAll}
            onExpandAll={onExpandAll}
            floatingComments={floatingComments}
            onToggleCommentMode={onToggleCommentMode}
          />
        )}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
      <AgentPanel
        isOpen={agentOpen}
        onToggle={onAgentToggle}
        selectedLineCount={selectedLineCount ?? 0}
        branchName={headBranch}
      />
      {mergeOpen && stackId && branches && onMergeClose && (
        <MergeFlowPanel
          isOpen={mergeOpen}
          onClose={onMergeClose}
          stackId={stackId}
          branches={branches}
          onSyncTrunk={onSync}
        />
      )}
    </div>
  );
}

AppShell.displayName = "AppShell";

export { AppShell };
export type { AppShellProps };

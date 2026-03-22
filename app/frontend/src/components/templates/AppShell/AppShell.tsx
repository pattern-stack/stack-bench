import type { ReactNode } from "react";
import { StackSidebar } from "@/components/organisms/StackSidebar";
import { AgentPanel } from "@/components/organisms/AgentPanel";
import { PRHeader } from "@/components/molecules/PRHeader";
import { ActionBar } from "@/components/molecules/ActionBar";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { BranchWithPR } from "@/types/stack";
import type { SidebarMode } from "@/types/sidebar";
import type { FileTreeNode } from "@/types/file-tree";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";

interface AppShellProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  activeBranch: BranchWithPR | null;
  agentOpen: boolean;
  onAgentToggle: () => void;
  selectedLineCount: number;
  children?: ReactNode;

  // Sidebar props
  sidebarMode: SidebarMode;
  onSidebarModeChange: (mode: SidebarMode) => void;
  diffFiles: DiffFileListItem[];
  fileTree: FileTreeNode | null;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  diffFileCount?: number;
  onRefresh?: () => void;
  changedFiles?: Map<string, ChangedFileInfo>;
}

/** Extract short branch name from full ref: "dug/frontend-mvp/3-stack-nav" → "3-stack-nav" */
function shortBranch(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

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
}: AppShellProps) {
  // Derive PRHeader props from the active branch
  const pr = activeBranch?.pull_request;
  const branchName = activeBranch?.branch.name ?? "";
  const title = pr?.title ?? shortBranch(branchName);
  const description = pr?.description ?? (pr ? null : "No pull request");
  const headBranch = shortBranch(branchName);

  // Base branch: for position 1, base is trunk. For others, it's the previous branch.
  const position = activeBranch?.branch.position ?? 1;
  const baseBranch = position <= 1 ? trunk : shortBranch(
    // Find branch at position - 1
    items[activeIndex - 1]?.title ?? trunk
  );

  // Display status: prefer PR state over branch state
  const displayStatus = pr?.state ?? activeBranch?.branch.state ?? "created";

  return (
    <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <StackSidebar
        stackName={stackName}
        trunk={trunk}
        items={items}
        activeIndex={activeIndex}
        onSelect={onSelect}
        sidebarMode={sidebarMode}
        onSidebarModeChange={onSidebarModeChange}
        diffFiles={diffFiles}
        fileTree={fileTree}
        selectedPath={selectedPath}
        onSelectFile={onSelectFile}
        diffFileCount={diffFileCount}
        onRefresh={onRefresh}
        changedFiles={changedFiles}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <PRHeader
          title={title}
          baseBranch={baseBranch}
          headBranch={headBranch}
          description={description}
        />
        <div className="flex-1 overflow-auto">
          {children}
        </div>
        <ActionBar status={displayStatus} />
      </main>
      <AgentPanel
        isOpen={agentOpen}
        onToggle={onAgentToggle}
        selectedLineCount={selectedLineCount}
        branchName={headBranch}
      />
    </div>
  );
}

AppShell.displayName = "AppShell";

export { AppShell };
export type { AppShellProps };

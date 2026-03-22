import { SidebarModeToggle } from "@/components/atoms/SidebarModeToggle";
import { StackConnector } from "@/components/molecules/StackConnector";
import { StackHeader } from "@/components/molecules/StackHeader";
import { ActivityLog } from "@/components/molecules/ActivityLog";
import { DiffFileList } from "@/components/molecules/DiffFileList";
import { FileTree } from "@/components/organisms/FileTree";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { SidebarMode } from "@/types/sidebar";
import type { FileTreeNode } from "@/types/file-tree";
import type { StackSummary, ActivityLogEntry } from "@/types/activity";

interface StackSidebarProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  summary: StackSummary;
  activityEntries: ActivityLogEntry[];
  onSync?: () => void;
  onRestackAll?: () => void;
  onMerge?: () => void;
  onClearActivity?: () => void;

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

function StackSidebar({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
  summary,
  activityEntries,
  onSync,
  onRestackAll,
  onMerge,
  onClearActivity,
  sidebarMode,
  onSidebarModeChange,
  diffFiles,
  fileTree,
  selectedPath,
  onSelectFile,
  diffFileCount,
  onRefresh,
  changedFiles,
}: StackSidebarProps) {
  return (
    <aside
      className="flex flex-col h-full w-[var(--sidebar-width)] border-r border-[var(--border)] bg-[var(--bg-surface)]"
    >
      {/* Header */}
      <StackHeader
        stackName={stackName}
        trunk={trunk}
        branchCount={items.length}
        summary={summary}
        onSync={onSync}
        onRestackAll={onRestackAll}
        onMerge={onMerge}
      />

      {/* Branch list */}
      <div className="shrink-0 overflow-y-auto px-1 py-1.5">
        <div className="px-3 pb-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
            Stack
          </span>
        </div>
        <StackConnector
          items={items}
          activeIndex={activeIndex}
          onSelect={onSelect}
        />
      </div>

      {/* Mode toggle */}
      <div className="px-3 py-1.5 border-t border-[var(--border-muted)]">
        <SidebarModeToggle
          mode={sidebarMode}
          onModeChange={onSidebarModeChange}
          diffFileCount={diffFileCount}
        />
      </div>

      {/* Tree area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {sidebarMode === "diffs" ? (
          <DiffFileList
            files={diffFiles}
            selectedPath={selectedPath}
            onSelectFile={onSelectFile}
          />
        ) : (
          fileTree && (
            <FileTree
              tree={fileTree}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              onRefresh={onRefresh}
              changedFiles={changedFiles}
            />
          )
        )}
      </div>

      {/* Activity log — hidden in files mode to make room for the explorer */}
      {sidebarMode === "diffs" && (
        <ActivityLog entries={activityEntries} onClear={onClearActivity} />
      )}
    </aside>
  );
}

StackSidebar.displayName = "StackSidebar";

export { StackSidebar };
export type { StackSidebarProps };

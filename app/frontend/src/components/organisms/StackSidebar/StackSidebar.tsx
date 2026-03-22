import { Button, Icon } from "@/components/atoms";
import { SidebarModeToggle } from "@/components/atoms/SidebarModeToggle";
import { StackConnector } from "@/components/molecules/StackConnector";
import { DiffFileList } from "@/components/molecules/DiffFileList";
import { FileTree } from "@/components/organisms/FileTree";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { SidebarMode } from "@/types/sidebar";
import type { FileTreeNode } from "@/types/file-tree";

interface StackSidebarProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  onRestackAll?: () => void;
  onPushStack?: () => void;

  sidebarMode: SidebarMode;
  onSidebarModeChange: (mode: SidebarMode) => void;
  diffFiles: DiffFileListItem[];
  fileTree: FileTreeNode | null;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  diffFileCount?: number;
  onRefresh?: () => void;
}

function StackSidebar({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
  onRestackAll,
  onPushStack,
  sidebarMode,
  onSidebarModeChange,
  diffFiles,
  fileTree,
  selectedPath,
  onSelectFile,
  diffFileCount,
  onRefresh,
}: StackSidebarProps) {
  return (
    <aside
      className="flex flex-col h-full w-[var(--sidebar-width)] border-r border-[var(--border)] bg-[var(--bg-surface)]"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-muted)]">
        <Icon name="git-branch" size="sm" className="text-[var(--fg-muted)]" />
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-semibold text-[var(--fg-default)] truncate">
            {stackName}
          </span>
          <span className="text-xs text-[var(--fg-subtle)]">
            {trunk}
          </span>
        </div>
      </div>

      {/* Branch list */}
      <div className="overflow-y-auto px-1 py-2">
        <div className="px-3 pb-2">
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
      <div className="px-3 py-2 border-t border-[var(--border-muted)]">
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
            />
          )
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-[var(--border-muted)]">
        <Button
          variant="subtle"
          size="sm"
          className="flex-1"
          onClick={onRestackAll}
          disabled={!onRestackAll}
        >
          <Icon name="refresh-cw" size="xs" />
          Restack all
        </Button>
        <Button
          variant="subtle"
          size="sm"
          className="flex-1"
          onClick={onPushStack}
          disabled={!onPushStack}
        >
          <Icon name="upload" size="xs" />
          Push stack
        </Button>
      </div>
    </aside>
  );
}

StackSidebar.displayName = "StackSidebar";

export { StackSidebar };
export type { StackSidebarProps };

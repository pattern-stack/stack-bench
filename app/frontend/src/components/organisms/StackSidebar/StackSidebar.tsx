import { Icon } from "@/components/atoms";
import { StackConnector } from "@/components/molecules/StackConnector";
import type { StackConnectorItem } from "@/components/molecules/StackConnector";

interface StackSidebarProps {
  stackName: string;
  trunk: string;
  items: StackConnectorItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function StackSidebar({
  stackName,
  trunk,
  items,
  activeIndex,
  onSelect,
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
      <div className="flex-1 overflow-y-auto px-1 py-2">
        <StackConnector
          items={items}
          activeIndex={activeIndex}
          onSelect={onSelect}
        />
      </div>
    </aside>
  );
}

StackSidebar.displayName = "StackSidebar";

export { StackSidebar };
export type { StackSidebarProps };

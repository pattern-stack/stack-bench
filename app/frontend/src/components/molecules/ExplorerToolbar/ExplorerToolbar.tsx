import { Icon } from "@/components/atoms/Icon";
import type { IconName } from "@/components/atoms/Icon";
import { cn } from "@/lib/utils";

interface ExplorerToolbarProps {
  title?: string;
  onCollapseAll: () => void;
  onExpandAll: () => void;
  onRefresh: () => void;
}

function ToolbarButton({
  icon,
  label,
  onClick,
}: {
  icon: IconName;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className={cn(
        "flex items-center justify-center w-6 h-6 rounded",
        "text-[var(--fg-muted)] hover:text-[var(--fg-default)]",
        "hover:bg-[var(--bg-surface-hover)] transition-colors"
      )}
    >
      <Icon name={icon} size="sm" />
    </button>
  );
}

function ExplorerToolbar({
  title = "EXPLORER",
  onCollapseAll,
  onExpandAll,
  onRefresh,
}: ExplorerToolbarProps) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border-muted)]">
      <span className="text-[11px] font-semibold tracking-wider uppercase text-[var(--fg-muted)] select-none">
        {title}
      </span>
      <div className="flex items-center gap-0.5">
        <ToolbarButton icon="collapse-all" label="Collapse All" onClick={onCollapseAll} />
        <ToolbarButton icon="expand-all" label="Expand All" onClick={onExpandAll} />
        <ToolbarButton icon="refresh-cw" label="Refresh" onClick={onRefresh} />
      </div>
    </div>
  );
}

ExplorerToolbar.displayName = "ExplorerToolbar";

export { ExplorerToolbar };
export type { ExplorerToolbarProps };

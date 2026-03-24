import { FileIcon } from "@/components/atoms/FileIcon";
import { cn } from "@/lib/utils";

interface FileTreeItemProps {
  name: string;
  type: "file" | "dir";
  depth: number;
  isOpen?: boolean;
  isActive?: boolean;
  onClick: () => void;
}

function FileTreeItem({
  name,
  type,
  depth,
  isOpen = false,
  isActive = false,
  onClick,
}: FileTreeItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center w-full gap-1.5 py-0.5 px-2 text-sm text-left rounded",
        "text-[13px]",
        "hover:bg-[var(--bg-surface-hover)] transition-colors",
        isActive && "bg-[var(--accent-muted)] text-[var(--accent)]",
        !isActive && "text-[var(--fg-default)]"
      )}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <FileIcon type={type} isOpen={isOpen} />
      <span className="truncate">{name}</span>
    </button>
  );
}

FileTreeItem.displayName = "FileTreeItem";

export { FileTreeItem };
export type { FileTreeItemProps };

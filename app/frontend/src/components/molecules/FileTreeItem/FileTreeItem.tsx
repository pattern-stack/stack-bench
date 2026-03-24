import { FileIcon } from "@/components/atoms/FileIcon";
import { IndentGuide } from "@/components/atoms/IndentGuide";
import { cn } from "@/lib/utils";

interface FileTreeItemProps {
  name: string;
  type: "file" | "dir";
  depth: number;
  isOpen?: boolean;
  isActive?: boolean;
  highlight?: string;
  onClick: () => void;
}

function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-[var(--accent-muted)] text-inherit rounded-sm px-px">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function FileTreeItem({
  name,
  type,
  depth,
  isOpen = false,
  isActive = false,
  highlight,
  onClick,
}: FileTreeItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex items-center w-full gap-1.5 py-0.5 pr-2 text-sm text-left rounded group",
        "text-[13px]",
        "hover:bg-[var(--bg-surface-hover)] transition-colors",
        isActive && "bg-[var(--accent-muted)] text-[var(--accent)]",
        !isActive && "text-[var(--fg-default)]"
      )}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <IndentGuide depth={depth} />
      <FileIcon type={type} isOpen={isOpen} fileName={name} />
      <span className="truncate">
        {highlight ? highlightMatch(name, highlight) : name}
      </span>
    </button>
  );
}

FileTreeItem.displayName = "FileTreeItem";

export { FileTreeItem };
export type { FileTreeItemProps };

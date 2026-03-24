import { useState, useCallback } from "react";
import { FileTreeItem } from "@/components/molecules/FileTreeItem";
import type { FileTreeNode } from "@/types/file-tree";

interface FileTreeProps {
  tree: FileTreeNode;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function sortChildren(children: FileTreeNode[]): FileTreeNode[] {
  return [...children].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function FileTree({ tree, selectedPath, onSelectFile }: FileTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    // Default: expand first level
    const initial = new Set<string>();
    if (tree.children) {
      for (const child of tree.children) {
        if (child.type === "dir") {
          initial.add(child.path);
        }
      }
    }
    return initial;
  });

  const toggleDir = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const renderNode = (node: FileTreeNode, depth: number) => {
    const isDir = node.type === "dir";
    const isOpen = expanded.has(node.path);

    return (
      <div key={node.path || node.name}>
        {/* Don't render the root "." node itself */}
        {node.path !== "" && (
          <FileTreeItem
            name={node.name}
            type={node.type}
            depth={depth}
            isOpen={isOpen}
            isActive={selectedPath === node.path}
            onClick={() =>
              isDir ? toggleDir(node.path) : onSelectFile(node.path)
            }
          />
        )}
        {isDir && (isOpen || node.path === "") && node.children && (
          <div>
            {sortChildren(node.children).map((child) =>
              renderNode(child, node.path === "" ? depth : depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="py-1 overflow-y-auto h-full">
      {renderNode(tree, 0)}
    </div>
  );
}

FileTree.displayName = "FileTree";

export { FileTree };
export type { FileTreeProps };

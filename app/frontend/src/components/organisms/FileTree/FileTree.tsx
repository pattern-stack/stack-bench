import { useState, useCallback, useRef } from "react";
import { FileTreeItem } from "@/components/molecules/FileTreeItem";
import { ExplorerToolbar } from "@/components/molecules/ExplorerToolbar";
import { SearchInput } from "@/components/atoms/SearchInput";
import type { FileTreeNode } from "@/types/file-tree";

import type { ChangeType } from "@/components/molecules/FileTreeItem";

interface ChangedFileInfo {
  changeType: ChangeType;
  additions: number;
  deletions: number;
}

interface FileTreeProps {
  tree: FileTreeNode;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  onRefresh?: () => void;
  changedFiles?: Map<string, ChangedFileInfo>;
}

function sortChildren(children: FileTreeNode[]): FileTreeNode[] {
  return [...children].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function collectAllDirs(node: FileTreeNode): string[] {
  const dirs: string[] = [];
  if (node.type === "dir" && node.path !== "") {
    dirs.push(node.path);
  }
  if (node.children) {
    for (const child of node.children) {
      dirs.push(...collectAllDirs(child));
    }
  }
  return dirs;
}

function collectMatchingPaths(
  node: FileTreeNode,
  query: string
): Set<string> {
  const matched = new Set<string>();
  const lowerQuery = query.toLowerCase();

  function walk(n: FileTreeNode, ancestors: string[]) {
    const matches = n.path.toLowerCase().includes(lowerQuery);
    if (matches && n.type === "file") {
      matched.add(n.path);
      for (const a of ancestors) matched.add(a);
    }
    if (n.children) {
      const nextAncestors = n.type === "dir" && n.path !== ""
        ? [...ancestors, n.path]
        : ancestors;
      for (const child of n.children) {
        walk(child, nextAncestors);
      }
    }
  }

  walk(node, []);
  return matched;
}

/** Check if a directory path has any changed files underneath it */
function hasDirtyDescendants(dirPath: string, changedFiles?: Map<string, ChangedFileInfo>): boolean {
  if (!changedFiles) return false;
  const prefix = dirPath ? dirPath + "/" : "";
  for (const path of changedFiles.keys()) {
    if (path.startsWith(prefix)) return true;
  }
  return false;
}

function FileTree({ tree, selectedPath, onSelectFile, onRefresh, changedFiles }: FileTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => {
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

  const [filterText, setFilterText] = useState("");
  const savedExpanded = useRef<Set<string> | null>(null);

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

  const collapseAll = useCallback(() => {
    setExpanded(new Set());
  }, []);

  const expandAll = useCallback(() => {
    setExpanded(new Set(collectAllDirs(tree)));
  }, [tree]);

  const handleFilterChange = useCallback(
    (value: string) => {
      if (value && !filterText) {
        savedExpanded.current = new Set(expanded);
      }
      setFilterText(value);

      if (value) {
        const matched = collectMatchingPaths(tree, value);
        const dirsToExpand = new Set<string>();
        for (const p of matched) {
          // Add parent dirs
          const parts = p.split("/");
          for (let i = 1; i < parts.length; i++) {
            dirsToExpand.add(parts.slice(0, i).join("/"));
          }
        }
        setExpanded(dirsToExpand);
      } else if (savedExpanded.current) {
        setExpanded(savedExpanded.current);
        savedExpanded.current = null;
      }
    },
    [filterText, expanded, tree]
  );

  const handleClearFilter = useCallback(() => {
    handleFilterChange("");
  }, [handleFilterChange]);

  const matchedPaths = filterText
    ? collectMatchingPaths(tree, filterText)
    : null;

  const renderNode = (node: FileTreeNode, depth: number) => {
    const isDir = node.type === "dir";
    const isOpen = expanded.has(node.path);

    // When filtering, hide non-matching nodes
    if (matchedPaths && node.path !== "" && !matchedPaths.has(node.path)) {
      return null;
    }

    return (
      <div key={node.path || node.name}>
        {node.path !== "" && (() => {
          const change = changedFiles?.get(node.path);
          return (
            <FileTreeItem
              name={node.name}
              type={node.type}
              depth={depth}
              isOpen={isOpen}
              isActive={selectedPath === node.path}
              highlight={filterText || undefined}
              changeType={change?.changeType}
              additions={change?.additions}
              deletions={change?.deletions}
              hasDirtyChildren={isDir && hasDirtyDescendants(node.path, changedFiles)}
              onClick={() =>
                isDir ? toggleDir(node.path) : onSelectFile(node.path)
              }
            />
          );
        })()}
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
    <div className="flex flex-col h-full">
      <ExplorerToolbar
        onCollapseAll={collapseAll}
        onExpandAll={expandAll}
        onRefresh={onRefresh ?? (() => {})}
      />
      <div className="px-2 py-1.5">
        <SearchInput
          placeholder="Search files..."
          value={filterText}
          onChange={(e) => handleFilterChange(e.target.value)}
          onClear={handleClearFilter}
        />
      </div>
      <div className="flex-1 py-1 overflow-y-auto">
        {renderNode(tree, 0)}
      </div>
    </div>
  );
}

FileTree.displayName = "FileTree";

export { FileTree };
export type { FileTreeProps, ChangedFileInfo };

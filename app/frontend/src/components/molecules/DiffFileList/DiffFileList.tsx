import { useState } from "react";
import { FileTreeItem } from "@/components/molecules/FileTreeItem";
import type { DiffFile } from "@/types/diff";

export interface DiffFileListItem {
  path: string;
  fileName: string;
  changeType: DiffFile["change_type"];
  additions: number;
  deletions: number;
}

interface DiffFileListProps {
  files: DiffFileListItem[];
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

interface DirNode {
  name: string;
  path: string;
  children: Map<string, DirNode>;
  files: DiffFileListItem[];
}

function buildTree(files: DiffFileListItem[]): DirNode {
  const root: DirNode = { name: "", path: "", children: new Map(), files: [] };

  for (const file of files) {
    const parts = file.path.split("/");
    let current = root;

    for (let i = 0; i < parts.length - 1; i++) {
      const dirName = parts[i]!;
      const dirPath = parts.slice(0, i + 1).join("/");
      if (!current.children.has(dirName)) {
        current.children.set(dirName, {
          name: dirName,
          path: dirPath,
          children: new Map(),
          files: [],
        });
      }
      current = current.children.get(dirName)!;
    }

    current.files.push(file);
  }

  // Compact: merge single-child directories into one row
  // e.g., app/frontend/src/ becomes one node instead of 3
  compactTree(root);

  return root;
}

function compactTree(node: DirNode): void {
  // Recurse first
  for (const child of node.children.values()) {
    compactTree(child);
  }

  // If this dir has exactly one child dir and no files, merge them
  if (node.children.size === 1 && node.files.length === 0) {
    const [, child] = [...node.children.entries()][0]!;
    // Merge: parent takes child's children and files, name becomes "parent/child"
    const mergedName = node.name ? `${node.name}/${child.name}` : child.name;
    node.name = mergedName;
    node.path = child.path;
    node.children = child.children;
    node.files = child.files;
  }
}

function RenderDirNode({
  node,
  depth,
  selectedPath,
  onSelectFile,
  collapsedDirs,
  onToggleDir,
}: {
  node: DirNode;
  depth: number;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  collapsedDirs: Set<string>;
  onToggleDir: (path: string) => void;
}) {
  const isOpen = !collapsedDirs.has(node.path);
  const sortedDirs = [...node.children.values()].sort((a, b) =>
    a.name.localeCompare(b.name)
  );
  const sortedFiles = [...node.files].sort((a, b) =>
    a.fileName.localeCompare(b.fileName)
  );

  return (
    <>
      {/* Render this directory (skip root) */}
      {depth >= 0 && (
        <FileTreeItem
          name={node.name}
          type="dir"
          depth={depth}
          isOpen={isOpen}
          hasDirtyChildren
          onClick={() => onToggleDir(node.path)}
        />
      )}

      {/* Render children when open (or always for root) */}
      {(isOpen || depth < 0) && (
        <>
          {sortedDirs.map((child) => (
            <RenderDirNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              collapsedDirs={collapsedDirs}
              onToggleDir={onToggleDir}
            />
          ))}
          {sortedFiles.map((file) => (
            <FileTreeItem
              key={file.path}
              name={file.fileName}
              type="file"
              depth={depth + 1}
              isActive={selectedPath === file.path}
              changeType={file.changeType}
              additions={file.additions}
              deletions={file.deletions}
              onClick={() => onSelectFile(file.path)}
            />
          ))}
        </>
      )}
    </>
  );
}

function DiffFileList({ files, selectedPath, onSelectFile }: DiffFileListProps) {
  const [collapsedDirs, setCollapsedDirs] = useState<Set<string>>(new Set());

  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[var(--fg-muted)] text-xs">No changed files</p>
      </div>
    );
  }

  const tree = buildTree(files);

  const handleToggleDir = (path: string) => {
    setCollapsedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className="py-1">
      <RenderDirNode
        node={tree}
        depth={-1}
        selectedPath={selectedPath}
        onSelectFile={onSelectFile}
        collapsedDirs={collapsedDirs}
        onToggleDir={handleToggleDir}
      />
    </div>
  );
}

DiffFileList.displayName = "DiffFileList";

export { DiffFileList };
export type { DiffFileListProps };

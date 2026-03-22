export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children: FileTreeNode[] | null;
  size: number | null;
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  language: string | null;
  lines: number;
  truncated: boolean;
}

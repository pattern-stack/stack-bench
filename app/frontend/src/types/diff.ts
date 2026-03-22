export interface DiffLine {
  type: "context" | "add" | "del" | "hunk";
  old_num: number | null;
  new_num: number | null;
  content: string;
  highlightedHtml?: string;
}

export interface DiffHunk {
  header: string;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  change_type: "added" | "modified" | "deleted" | "renamed";
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
}

export interface DiffData {
  files: DiffFile[];
  total_additions: number;
  total_deletions: number;
}

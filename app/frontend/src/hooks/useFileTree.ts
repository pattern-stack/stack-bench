import { useState } from "react";
import type { FileTreeNode } from "@/types/file-tree";
import { mockFileTree } from "@/lib/mock-file-data";

interface UseFileTreeResult {
  data: FileTreeNode | null;
  loading: boolean;
  error: string | null;
}

export function useFileTree(_branchId?: string): UseFileTreeResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [data] = useState<FileTreeNode | null>(mockFileTree);
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  return { data, loading, error };
}

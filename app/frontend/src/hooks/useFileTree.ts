import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { FileTreeNode } from "@/types/file-tree";

interface UseFileTreeResult {
  data: FileTreeNode | null;
  loading: boolean;
  error: string | null;
}

export const fileTreeKeys = {
  all: ["file-tree"] as const,
  tree: (stackId: string, branchId: string) =>
    [...fileTreeKeys.all, stackId, branchId] as const,
};

export function useFileTree(
  stackId: string | undefined,
  branchId?: string
): UseFileTreeResult {
  const {
    data = null,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: fileTreeKeys.tree(stackId ?? "", branchId ?? ""),
    queryFn: () =>
      apiClient.get<FileTreeNode>(
        `/api/v1/stacks/${stackId}/branches/${branchId}/tree`
      ),
    enabled: !!stackId && !!branchId,
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

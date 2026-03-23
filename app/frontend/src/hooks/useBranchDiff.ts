import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { DiffData } from "@/types/diff";

interface UseBranchDiffResult {
  data: DiffData | null;
  loading: boolean;
  error: string | null;
}

export const branchDiffKeys = {
  all: ["branch-diff"] as const,
  diff: (stackId: string, branchId: string) =>
    [...branchDiffKeys.all, stackId, branchId] as const,
};

export function useBranchDiff(
  stackId: string | undefined,
  branchId: string | undefined
): UseBranchDiffResult {
  const {
    data = null,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: branchDiffKeys.diff(stackId ?? "", branchId ?? ""),
    queryFn: () =>
      apiClient.get<DiffData>(
        `/api/v1/stacks/${stackId}/branches/${branchId}/diff`
      ),
    enabled: !!stackId && !!branchId,
    staleTime: Infinity, // SHA-addressed — never changes for a given branch
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

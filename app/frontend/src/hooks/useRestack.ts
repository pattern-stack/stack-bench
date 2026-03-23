import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { stackDetailKeys } from "@/hooks/useStackDetail";

interface RestackBranchResult {
  branch_name: string;
  position: number;
  old_sha: string | null;
  new_sha: string | null;
  status: "rebased" | "conflict" | "skipped" | "up_to_date" | "error";
  error: string | null;
  conflicting_files: string[];
}

interface RestackResponse {
  success: boolean;
  branches: RestackBranchResult[];
  error: string | null;
}

export function useRestack(stackId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (fromPosition: number = 1) => {
      if (!stackId) {
        throw new Error("stackId is required");
      }
      return apiClient.post<RestackResponse>(
        `/api/v1/stacks/${stackId}/restack`,
        { from_position: fromPosition },
      );
    },
    onSuccess: () => {
      if (stackId) {
        queryClient.invalidateQueries({ queryKey: stackDetailKeys.detail(stackId) });
      }
    },
  });
}

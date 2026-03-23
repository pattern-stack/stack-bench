import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { stackDetailKeys } from "@/hooks/useStackDetail";

export function useMarkReady(stackId?: string, branchId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!stackId || !branchId) {
        throw new Error("stackId and branchId are required");
      }
      return apiClient.post(
        `/api/v1/stacks/${stackId}/branches/${branchId}/pr/ready`,
      );
    },
    onSuccess: () => {
      if (stackId) {
        queryClient.invalidateQueries({ queryKey: stackDetailKeys.detail(stackId) });
      }
    },
  });
}

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { StackDetail } from "@/types/stack";

export const stackDetailKeys = {
  all: ["stack-detail"] as const,
  detail: (id: string) => [...stackDetailKeys.all, id] as const,
};

export function useStackDetail(stackId?: string) {
  const { data = null, isLoading: loading, error: queryError } = useQuery({
    queryKey: stackDetailKeys.detail(stackId ?? ""),
    queryFn: () => apiClient.get<StackDetail>(`/api/v1/stacks/${stackId}/detail`),
    enabled: !!stackId,
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

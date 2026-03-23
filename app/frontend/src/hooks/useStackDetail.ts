import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { StackDetail } from "@/types/stack";

const DEFAULT_STACK_ID = "d285f701-e77c-46a2-949a-8b486de3c3b9"; // round-2-polish (seeded)

export const stackDetailKeys = {
  all: ["stack-detail"] as const,
  detail: (id: string) => [...stackDetailKeys.all, id] as const,
};

export function useStackDetail(stackId?: string) {
  const id = stackId ?? DEFAULT_STACK_ID;

  const { data = null, isLoading: loading, error: queryError } = useQuery({
    queryKey: stackDetailKeys.detail(id),
    queryFn: () => apiClient.get<StackDetail>(`/api/v1/stacks/${id}/detail`),
    enabled: !!id,
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { stackDetailKeys } from "@/hooks/useStackDetail";
import type { MergeCascadeDetail, CascadeState } from "@/types/merge-cascade";

const TERMINAL_STATES: CascadeState[] = ["completed", "failed", "cancelled"];

export function useMergeCascade(stackId?: string) {
  const queryClient = useQueryClient();
  const [cascadeId, setCascadeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isActive = (state?: CascadeState) =>
    !!state && !TERMINAL_STATES.includes(state);

  const { data: cascade = null, isLoading: isPolling } = useQuery({
    queryKey: ["merge-cascade", stackId, cascadeId] as const,
    queryFn: () =>
      apiClient.get<MergeCascadeDetail>(
        `/api/v1/stacks/${stackId}/merge-cascade/${cascadeId}`
      ),
    enabled: !!stackId && !!cascadeId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return isActive(state) ? 2000 : false;
    },
  });

  // Stop polling and refresh stack detail when cascade reaches terminal state
  const cascadeState = cascade?.state;
  if (cascadeState && TERMINAL_STATES.includes(cascadeState) && stackId) {
    // Invalidate stack detail so sidebar refreshes
    queryClient.invalidateQueries({ queryKey: stackDetailKeys.detail(stackId) });
  }

  const startCascade = useCallback(
    async (mergeUpTo?: number) => {
      if (!stackId) return;
      setError(null);
      try {
        const body = mergeUpTo != null ? { merge_up_to: mergeUpTo } : undefined;
        const result = await apiClient.post<MergeCascadeDetail>(
          `/api/v1/stacks/${stackId}/merge-cascade`,
          body
        );
        setCascadeId(result.id);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : typeof err === "object" && err !== null && "message" in err
              ? String((err as { message: unknown }).message)
              : "Failed to start merge cascade";
        setError(message);
      }
    },
    [stackId]
  );

  const cancelCascade = useCallback(async () => {
    if (!stackId || !cascadeId) return;
    try {
      await apiClient.post(
        `/api/v1/stacks/${stackId}/merge-cascade/${cascadeId}/cancel`
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to cancel cascade";
      setError(message);
    }
  }, [stackId, cascadeId]);

  const reset = useCallback(() => {
    setCascadeId(null);
    setError(null);
  }, []);

  return {
    cascade,
    isActive: isActive(cascade?.state),
    isPolling,
    startCascade,
    cancelCascade,
    reset,
    error,
  };
}

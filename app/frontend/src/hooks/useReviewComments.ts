import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

export interface ReviewComment {
  id: string;
  reference_number: string | null;
  pull_request_id: string;
  branch_id: string;
  path: string;
  line_key: string;
  line_number: number | null;
  side: string | null;
  body: string;
  author: string;
  external_id: number | null;
  resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateCommentPayload {
  pull_request_id: string;
  path: string;
  line_key: string;
  body: string;
  author: string;
  line_number?: number | null;
  side?: string | null;
}

export const reviewCommentKeys = {
  all: ["review-comments"] as const,
  list: (stackId: string, branchId: string) =>
    [...reviewCommentKeys.all, stackId, branchId] as const,
};

export function useReviewComments(
  stackId: string | undefined,
  branchId: string | undefined
) {
  const {
    data = null,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: reviewCommentKeys.list(stackId ?? "", branchId ?? ""),
    queryFn: () =>
      apiClient.get<ReviewComment[]>(
        `/api/v1/stacks/${stackId}/branches/${branchId}/comments`
      ),
    enabled: !!stackId && !!branchId,
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

export function useCreateComment(
  stackId: string | undefined,
  branchId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateCommentPayload) =>
      apiClient.post<ReviewComment>(
        `/api/v1/stacks/${stackId}/branches/${branchId}/comments`,
        payload
      ),
    onSuccess: () => {
      if (stackId && branchId) {
        queryClient.invalidateQueries({
          queryKey: reviewCommentKeys.list(stackId, branchId),
        });
      }
    },
  });
}

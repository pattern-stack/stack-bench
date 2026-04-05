import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { TaskDetail } from "@/types/task";

export const taskDetailKeys = {
  all: ["task-detail"] as const,
  detail: (id: string) => [...taskDetailKeys.all, id] as const,
};

export function useTaskDetail(taskId: string | undefined) {
  const { data = null, isLoading, error } = useQuery({
    queryKey: taskDetailKeys.detail(taskId ?? ""),
    queryFn: () =>
      apiClient.get<TaskDetail>(`/api/v1/tasks/${taskId}/detail`),
    enabled: !!taskId,
  });

  return { data, loading: isLoading, error: error ? String(error) : null };
}

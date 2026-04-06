import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { Task } from "@/types/task";

export const taskListKeys = {
  all: ["task-list"] as const,
  byProject: (projectId: string) => [...taskListKeys.all, projectId] as const,
};

export function useTaskList(projectId: string | undefined) {
  const { data = [], isLoading, error } = useQuery({
    queryKey: taskListKeys.byProject(projectId ?? ""),
    queryFn: () =>
      apiClient.get<Task[]>("/api/v1/tasks/", { project_id: projectId }),
    enabled: !!projectId,
  });

  return { data, loading: isLoading, error: error ? String(error) : null };
}

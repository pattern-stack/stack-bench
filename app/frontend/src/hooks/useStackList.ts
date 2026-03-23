import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { Stack } from "@/types/stack";

export const stackListKeys = {
  all: ["stack-list"] as const,
  byProject: (projectId: string) => [...stackListKeys.all, projectId] as const,
};

export function useStackList(projectId: string | undefined) {
  const { data = [], isLoading, error } = useQuery({
    queryKey: stackListKeys.byProject(projectId ?? ""),
    queryFn: () =>
      apiClient.get<Stack[]>("/api/v1/stacks/", { project_id: projectId }),
    enabled: !!projectId,
  });

  return { data, loading: isLoading, error: error ? String(error) : null };
}

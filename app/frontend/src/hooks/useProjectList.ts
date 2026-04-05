import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";

interface Project {
  id: string;
  name: string;
  github_repo: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export const projectListKeys = {
  all: ["project-list"] as const,
};

export function useProjectList() {
  const { data = [], isLoading, error } = useQuery({
    queryKey: projectListKeys.all,
    queryFn: () => apiClient.get<Project[]>("/api/v1/projects/"),
  });

  return { data, loading: isLoading, error: error ? String(error) : null };
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { projectListKeys } from "@/hooks/useProjectList";

interface CreateLocalProjectInput {
  name: string;
  local_path: string;
  description?: string;
}

interface CreateLocalProjectResult {
  project_id: string;
  workspace_id: string;
  project_name: string;
}

export function useCreateLocalProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateLocalProjectInput) =>
      apiClient.post<CreateLocalProjectResult>(
        "/api/v1/projects/setup",
        input
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectListKeys.all });
    },
  });
}

export type { CreateLocalProjectInput, CreateLocalProjectResult };

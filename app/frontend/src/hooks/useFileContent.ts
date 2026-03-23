import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import type { FileContent } from "@/types/file-tree";

interface UseFileContentResult {
  data: FileContent | null;
  loading: boolean;
  error: string | null;
}

export const fileContentKeys = {
  all: ["file-content"] as const,
  file: (stackId: string, branchId: string, path: string) =>
    [...fileContentKeys.all, stackId, branchId, path] as const,
};

export function useFileContent(
  stackId: string | undefined,
  branchId: string | undefined,
  path: string | null
): UseFileContentResult {
  const {
    data = null,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: fileContentKeys.file(stackId ?? "", branchId ?? "", path ?? ""),
    queryFn: () =>
      apiClient.get<FileContent>(
        `/api/v1/stacks/${stackId}/branches/${branchId}/files/${path}`
      ),
    enabled: !!stackId && !!branchId && !!path,
  });

  const error = queryError ? String(queryError) : null;

  return { data, loading, error };
}

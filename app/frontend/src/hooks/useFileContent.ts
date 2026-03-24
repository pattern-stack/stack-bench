import { useState } from "react";
import type { FileContent } from "@/types/file-tree";
import { getMockFileContent } from "@/lib/mock-file-data";

interface UseFileContentResult {
  data: FileContent | null;
  loading: boolean;
  error: string | null;
}

export function useFileContent(
  _branchId: string | undefined,
  path: string | null
): UseFileContentResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  const data = path ? getMockFileContent(path) : null;

  return { data, loading, error };
}

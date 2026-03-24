import { useState } from "react";
import type { DiffData } from "@/types/diff";
import { mockDiffDataByBranch } from "@/lib/mock-diff-data";

interface UseBranchDiffResult {
  data: DiffData | null;
  loading: boolean;
  error: string | null;
}

export function useBranchDiff(branchId: string | undefined): UseBranchDiffResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  const data = branchId ? (mockDiffDataByBranch[branchId] ?? null) : null;

  return { data, loading, error };
}

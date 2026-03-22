import { useState } from "react";
import type { StackDetail } from "@/types/stack";
import { mockStackDetail } from "@/lib/mock-data";

interface UseStackDetailResult {
  data: StackDetail | null;
  loading: boolean;
  error: string | null;
}

export function useStackDetail(_stackId?: string): UseStackDetailResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [data] = useState<StackDetail | null>(mockStackDetail);
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  return { data, loading, error };
}

import { useMemo } from "react";
import type { BranchWithPR } from "@/types/stack";
import type { MergeReadiness, MergeBlocker } from "@/types/merge-cascade";

/** Status values that indicate an open/submittable PR */
const SUBMITTABLE_STATUSES = new Set(["open", "reviewing", "review", "approved", "ready"]);

/**
 * Compute merge readiness for each branch in a stack.
 * Pure client-side derivation from existing BranchWithPR data.
 * Returns a Map keyed by branch ID.
 */
export function useMergeReadiness(branches: BranchWithPR[]): Map<string, MergeReadiness> {
  return useMemo(() => {
    const map = new Map<string, MergeReadiness>();

    for (const b of branches) {
      const blockers: MergeBlocker[] = [];

      // Already merged — excluded from cascade
      if (b.branch.state === "merged" || b.pull_request?.state === "merged") {
        map.set(b.branch.id, {
          ready: false,
          blockers: [{ kind: "already_merged", label: "Already merged" }],
        });
        continue;
      }

      // No pull request
      if (!b.pull_request) {
        blockers.push({ kind: "no_pr", label: "No PR" });
      } else if (!SUBMITTABLE_STATUSES.has(b.pull_request.state)) {
        // PR exists but not in a submittable state
        blockers.push({ kind: "not_submitted", label: "Not submitted" });
      }

      // Needs restack
      if (b.needs_restack) {
        blockers.push({ kind: "needs_restack", label: "Needs restack" });
      }

      // CI status — currently not available in BranchWithPR, placeholder for future
      // When CI data becomes available, check here and push ci_failing blocker

      map.set(b.branch.id, {
        ready: blockers.length === 0,
        blockers,
      });
    }

    return map;
  }, [branches]);
}

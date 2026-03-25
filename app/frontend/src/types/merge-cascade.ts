export type CascadeState = "pending" | "running" | "completed" | "failed" | "cancelled";

export type CascadeStepState =
  | "pending"
  | "retargeting"
  | "rebasing"
  | "ci_pending"
  | "completing"
  | "merged"
  | "conflict"
  | "failed"
  | "skipped";

export interface MergeCascadeDetail {
  id: string;
  stack_id: string;
  triggered_by: string;
  current_position: number;
  state: CascadeState;
  error: string | null;
  created_at: string;
  updated_at: string;
  steps: CascadeStepDetail[];
}

export interface CascadeStepDetail {
  id: string;
  cascade_id: string;
  branch_id: string;
  pull_request_id: string | null;
  position: number;
  state: CascadeStepState;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  branch_name: string;
  pr_number: number | null;
  pr_title: string | null;
}

export type MergeBlockerKind = "ci_failing" | "needs_restack" | "no_pr" | "not_submitted" | "already_merged";

export interface MergeBlocker {
  kind: MergeBlockerKind;
  label: string;
}

export interface MergeReadiness {
  ready: boolean;
  blockers: MergeBlocker[];
}

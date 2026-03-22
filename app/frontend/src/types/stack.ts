export interface Stack {
  id: string;
  reference_number: string | null;
  project_id: string;
  name: string;
  base_branch_id: string | null;
  trunk: string;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface Branch {
  id: string;
  reference_number: string | null;
  stack_id: string;
  workspace_id: string;
  name: string;
  position: number;
  head_sha: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface PullRequest {
  id: string;
  reference_number: string | null;
  branch_id: string;
  external_id: number | null;
  external_url: string | null;
  title: string;
  description: string | null;
  review_notes: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface BranchWithPR {
  branch: Branch;
  pull_request: PullRequest | null;
}

export interface StackDetail {
  stack: Stack;
  branches: BranchWithPR[];
}

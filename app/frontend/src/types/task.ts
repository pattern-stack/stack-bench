export interface Task {
  id: string;
  reference_number: string | null;
  title: string;
  description: string | null;
  priority: "critical" | "high" | "medium" | "low" | "none";
  issue_type: "story" | "bug" | "task" | "spike" | "epic";
  state:
    | "backlog"
    | "ready"
    | "in_progress"
    | "in_review"
    | "done"
    | "cancelled";
  status_category: "todo" | "in_progress" | "done";
  work_phase: string | null;
  project_id: string | null;
  assignee_id: string | null;
  sprint_id: string | null;
  external_id: string | null;
  external_url: string | null;
  provider: "github" | "linear" | "local";
  created_at: string;
  updated_at: string;
}

export interface AgentPhase {
  id: string;
  phase: string;
  runner_type: string;
  state: "pending" | "running" | "complete" | "failed";
  duration_ms: number | null;
  attempt: number;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  reference_number: string | null;
  state: string;
  task_id: string | null;
  repo_url: string;
  repo_branch: string;
  issue_number: number | null;
  issue_title: string | null;
  current_phase: string | null;
  error_message: string | null;
  artifacts: Record<string, unknown>;
  gate_decisions: unknown[];
  created_at: string;
  updated_at: string;
}

export interface TaskDetail {
  task: Task;
  job: Job | null;
  agent_runs: AgentPhase[];
}

export type CIStatus = "pass" | "fail" | "pending" | "none";

export interface ActivityLogEntry {
  id: string;
  operation: "sync" | "merge" | "restack" | "push";
  description: string;
  timestamp: string; // ISO 8601
}

export interface StackSummary {
  branchCount: number;
  merged: number;
  open: number;
  needsRestack: number;
  draft: number;
}

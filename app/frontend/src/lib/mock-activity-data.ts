import type { ActivityLogEntry } from "@/types/activity";

function minutesAgo(n: number): string {
  return new Date(Date.now() - n * 60 * 1000).toISOString();
}

export const mockActivityEntries: ActivityLogEntry[] = [
  {
    id: "act-001",
    operation: "sync",
    description: "Synced trunk (main) — 2 new commits",
    timestamp: minutesAgo(2),
  },
  {
    id: "act-002",
    operation: "restack",
    description: "Restacked 6-dirty-state-consolidation onto updated 5-sidebar-merge",
    timestamp: minutesAgo(5),
  },
  {
    id: "act-003",
    operation: "push",
    description: "Pushed 5-sidebar-merge to origin",
    timestamp: minutesAgo(12),
  },
  {
    id: "act-004",
    operation: "merge",
    description: "Merged #65 (2-design-polish) into main",
    timestamp: minutesAgo(28),
  },
  {
    id: "act-005",
    operation: "push",
    description: "Pushed 4-agent-panel to origin",
    timestamp: minutesAgo(45),
  },
  {
    id: "act-006",
    operation: "sync",
    description: "Synced trunk (main) — up to date",
    timestamp: minutesAgo(58),
  },
];

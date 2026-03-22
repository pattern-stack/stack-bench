import { Badge } from "@/components/atoms";
import type { BadgeProps } from "@/components/atoms";

type StatusString =
  | "draft"
  | "created"
  | "pushed"
  | "local"
  | "open"
  | "reviewing"
  | "review"
  | "approved"
  | "ready"
  | "submitted"
  | "merged"
  | "closed"
  | "active";

const statusColorMap: Record<StatusString, BadgeProps["color"]> = {
  draft: "default",
  created: "default",
  pushed: "default",
  local: "default",
  active: "accent",
  open: "accent",
  reviewing: "accent",
  review: "purple",
  approved: "purple",
  ready: "purple",
  submitted: "yellow",
  merged: "green",
  closed: "red",
};

const statusLabelMap: Record<StatusString, string> = {
  draft: "Draft",
  created: "Local",
  pushed: "Pushed",
  local: "Local",
  active: "Active",
  open: "Open",
  reviewing: "Reviewing",
  review: "Review",
  approved: "Approved",
  ready: "Ready",
  submitted: "Submitted",
  merged: "Merged",
  closed: "Closed",
};

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const key = status as StatusString;
  const color = statusColorMap[key] ?? "default";
  const label = statusLabelMap[key] ?? status;

  return (
    <Badge size="sm" color={color}>
      {label}
    </Badge>
  );
}

StatusBadge.displayName = "StatusBadge";

export { StatusBadge };
export type { StatusBadgeProps, StatusString };

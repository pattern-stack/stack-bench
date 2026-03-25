import { Badge } from "@/components/atoms/Badge";
import type { BadgeProps } from "@/components/atoms/Badge";

type BlockerBadgeKind = "ci_failing" | "needs_restack" | "no_pr" | "not_submitted";

interface BlockerBadgeProps {
  kind: BlockerBadgeKind;
}

const blockerColorMap: Record<BlockerBadgeKind, BadgeProps["color"]> = {
  ci_failing: "red",
  needs_restack: "yellow",
  no_pr: "default",
  not_submitted: "default",
};

const blockerLabelMap: Record<BlockerBadgeKind, string> = {
  ci_failing: "CI failing",
  needs_restack: "Needs restack",
  no_pr: "No PR",
  not_submitted: "Not submitted",
};

function BlockerBadge({ kind }: BlockerBadgeProps) {
  return (
    <Badge size="sm" color={blockerColorMap[kind]}>
      {blockerLabelMap[kind]}
    </Badge>
  );
}

BlockerBadge.displayName = "BlockerBadge";

export { BlockerBadge };
export type { BlockerBadgeProps, BlockerBadgeKind };

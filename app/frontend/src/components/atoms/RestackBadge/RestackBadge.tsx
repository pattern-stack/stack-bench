import { Badge } from "@/components/atoms/Badge";

interface RestackBadgeProps {
  className?: string;
}

function RestackBadge({ className }: RestackBadgeProps) {
  return (
    <Badge size="sm" color="yellow" className={className}>
      Restack
    </Badge>
  );
}

RestackBadge.displayName = "RestackBadge";

export { RestackBadge };
export type { RestackBadgeProps };

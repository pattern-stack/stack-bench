import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface CountBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  count: number;
}

const CountBadge = forwardRef<HTMLSpanElement, CountBadgeProps>(
  ({ count, className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-medium leading-none bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] border border-[var(--border-muted)]",
        className
      )}
      {...props}
    >
      {count}
    </span>
  )
);

CountBadge.displayName = "CountBadge";

export { CountBadge };
export type { CountBadgeProps };

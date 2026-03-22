import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full font-medium leading-none whitespace-nowrap",
  {
    variants: {
      size: {
        sm: "px-1.5 py-0.5 text-[10px]",
        default: "px-2 py-0.5 text-xs",
      },
      color: {
        default:
          "bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] border border-[var(--border-muted)]",
        green:
          "bg-[var(--green-bg)] text-[var(--green)] border border-[var(--green)]/20",
        red:
          "bg-[var(--red-bg)] text-[var(--red)] border border-[var(--red)]/20",
        purple:
          "bg-[var(--purple)]/10 text-[var(--purple)] border border-[var(--purple)]/20",
        yellow:
          "bg-[var(--yellow)]/10 text-[var(--yellow)] border border-[var(--yellow)]/20",
        accent:
          "bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/20",
      },
    },
    defaultVariants: {
      size: "default",
      color: "default",
    },
  }
);

type BadgeVariants = VariantProps<typeof badgeVariants>;

interface BadgeProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, "color">,
    BadgeVariants {}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, size, color, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(badgeVariants({ size, color }), className)}
      {...props}
    />
  )
);

Badge.displayName = "Badge";

export { Badge, badgeVariants };
export type { BadgeProps };

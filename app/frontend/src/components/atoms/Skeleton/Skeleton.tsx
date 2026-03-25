import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: string;
  height?: string;
}

const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, width, height, style, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded bg-[var(--bg-surface-hover)] animate-pulse",
        className
      )}
      style={{ width, height, ...style }}
      {...props}
    />
  )
);

Skeleton.displayName = "Skeleton";

export { Skeleton };
export type { SkeletonProps };

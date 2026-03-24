import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface TabProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

const Tab = forwardRef<HTMLButtonElement, TabProps>(
  ({ active = false, className, children, ...props }, ref) => (
    <button
      ref={ref}
      role="tab"
      aria-selected={active}
      className={cn(
        "relative inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2",
        active
          ? "text-[var(--fg-default)] border-[var(--accent)]"
          : "text-[var(--fg-muted)] border-transparent hover:text-[var(--fg-default)] hover:border-[var(--border)]",
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
);

Tab.displayName = "Tab";

export { Tab };
export type { TabProps };

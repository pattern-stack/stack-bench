import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";

interface ViewedToggleProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  viewed: boolean;
  onChange: (viewed: boolean) => void;
}

const ViewedToggle = forwardRef<HTMLButtonElement, ViewedToggleProps>(
  ({ viewed, onChange, className, ...props }, ref) => (
    <button
      ref={ref}
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onChange(!viewed);
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors select-none cursor-pointer",
        viewed
          ? "bg-[var(--accent-emerald-dim)] text-[var(--accent-emerald)]"
          : "bg-transparent border border-[var(--border)] text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:border-[var(--fg-subtle)]",
        className
      )}
      {...props}
    >
      {viewed && <Icon name="check" size="xs" className="shrink-0" />}
      {viewed ? "Viewed" : "Mark viewed"}
    </button>
  )
);

ViewedToggle.displayName = "ViewedToggle";

export { ViewedToggle };
export type { ViewedToggleProps };

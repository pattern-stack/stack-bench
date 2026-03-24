import { forwardRef, type InputHTMLAttributes } from "react";
import { Icon } from "@/components/atoms/Icon";
import { cn } from "@/lib/utils";

interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  onClear?: () => void;
}

const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, value, onClear, ...props }, ref) => {
    const hasValue = value !== undefined && value !== "";

    return (
      <div className={cn("relative flex items-center", className)}>
        <Icon
          name="search"
          size="xs"
          className="absolute left-2 text-[var(--fg-subtle)] pointer-events-none"
        />
        <input
          ref={ref}
          type="text"
          value={value}
          className={cn(
            "w-full h-7 pl-7 pr-7 text-xs rounded",
            "bg-[var(--bg-inset)] border border-[var(--border-muted)]",
            "text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)]",
            "focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]",
            "transition-colors"
          )}
          {...props}
        />
        {hasValue && onClear && (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-1.5 p-0.5 rounded hover:bg-[var(--bg-surface-hover)] text-[var(--fg-subtle)] hover:text-[var(--fg-muted)] transition-colors"
          >
            <Icon name="x-circle" size="xs" />
          </button>
        )}
      </div>
    );
  }
);

SearchInput.displayName = "SearchInput";

export { SearchInput };
export type { SearchInputProps };

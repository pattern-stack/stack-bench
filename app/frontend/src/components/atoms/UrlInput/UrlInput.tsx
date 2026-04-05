import { forwardRef, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";

interface UrlInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  className?: string;
}

const UrlInput = forwardRef<HTMLInputElement, UrlInputProps>(
  ({ value, onChange, onSubmit, placeholder = "https://...", className }, ref) => {
    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onSubmit();
      }
    };

    return (
      <div
        className={cn(
          "flex items-center gap-1.5 flex-1 min-w-0 h-7 px-2 rounded-md bg-[var(--bg-inset)] border border-[var(--border)]",
          className
        )}
      >
        <Icon name="globe" size="xs" className="shrink-0 text-[var(--fg-subtle)]" />
        <input
          ref={ref}
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1 min-w-0 bg-transparent text-xs text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] font-[family-name:var(--font-mono)] outline-none border-none"
        />
      </div>
    );
  }
);

UrlInput.displayName = "UrlInput";

export { UrlInput };
export type { UrlInputProps };

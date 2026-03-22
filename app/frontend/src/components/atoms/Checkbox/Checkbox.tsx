import { cn } from "@/lib/utils";

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  className?: string;
}

function Checkbox({ checked, onChange, label, className }: CheckboxProps) {
  return (
    <label
      className={cn(
        "inline-flex items-center gap-1.5 cursor-pointer select-none text-xs text-[var(--fg-muted)] hover:text-[var(--fg-default)] transition-colors",
        className
      )}
    >
      <span
        role="checkbox"
        aria-checked={checked}
        tabIndex={0}
        onClick={() => onChange(!checked)}
        onKeyDown={(e) => {
          if (e.key === " " || e.key === "Enter") {
            e.preventDefault();
            onChange(!checked);
          }
        }}
        className={cn(
          "inline-flex items-center justify-center w-4 h-4 rounded border transition-colors",
          checked
            ? "bg-[var(--accent)] border-[var(--accent)]"
            : "bg-transparent border-[var(--fg-subtle)] hover:border-[var(--fg-muted)]"
        )}
      >
        {checked && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width={10}
            height={10}
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fff"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
      </span>
      {label && <span>{label}</span>}
    </label>
  );
}

Checkbox.displayName = "Checkbox";

export { Checkbox };
export type { CheckboxProps };

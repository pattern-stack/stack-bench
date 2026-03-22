import { cn } from "@/lib/utils";
import type { SidebarMode } from "@/types/sidebar";

interface SidebarModeToggleProps {
  mode: SidebarMode;
  onModeChange: (mode: SidebarMode) => void;
  diffFileCount?: number;
}

function SidebarModeToggle({ mode, onModeChange, diffFileCount }: SidebarModeToggleProps) {
  const options: { id: SidebarMode; label: string; count?: number }[] = [
    { id: "diffs", label: "Diffs", count: diffFileCount },
    { id: "files", label: "Files" },
  ];

  return (
    <div className="flex gap-0.5 rounded-md bg-[var(--bg-canvas)] p-0.5">
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onModeChange(opt.id)}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
            mode === opt.id
              ? "bg-[var(--accent-muted)] text-[var(--accent)]"
              : "text-[var(--fg-muted)] hover:text-[var(--fg-default)]"
          )}
        >
          {opt.label}
          {opt.count !== undefined && opt.count > 0 && (
            <span
              className={cn(
                "inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full px-1 text-[10px] font-semibold leading-none",
                mode === opt.id
                  ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                  : "bg-[var(--fg-subtle)]/15 text-[var(--fg-subtle)]"
              )}
            >
              {opt.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

SidebarModeToggle.displayName = "SidebarModeToggle";

export { SidebarModeToggle };
export type { SidebarModeToggleProps };

import { Icon } from "@/components/atoms/Icon";
import { getExtensionColor } from "@/components/atoms/FileIcon";
import { cn } from "@/lib/utils";

interface PathBarProps {
  path: string;
  onNavigate?: (segmentPath: string) => void;
}

function PathBar({ path, onNavigate }: PathBarProps) {
  const segments = path.split("/").filter(Boolean);

  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)] text-xs font-[family-name:var(--font-mono)] overflow-x-auto">
      {segments.map((segment, i) => {
        const isLast = i === segments.length - 1;
        const segmentPath = segments.slice(0, i + 1).join("/");
        const color = isLast ? getExtensionColor(segment) : undefined;

        return (
          <span key={segmentPath} className="flex items-center gap-1 shrink-0">
            {i > 0 && (
              <Icon
                name="chevron-right"
                size="xs"
                className="text-[var(--fg-subtle)]"
              />
            )}
            <button
              type="button"
              onClick={() => onNavigate?.(segmentPath)}
              className={cn(
                "hover:text-[var(--accent)] transition-colors rounded px-0.5",
                isLast ? "font-semibold" : "text-[var(--fg-muted)]"
              )}
              style={isLast && color ? { color } : undefined}
            >
              {segment}
            </button>
          </span>
        );
      })}
    </div>
  );
}

PathBar.displayName = "PathBar";

export { PathBar };
export type { PathBarProps };

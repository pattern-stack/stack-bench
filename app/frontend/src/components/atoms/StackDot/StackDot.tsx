import { cn } from "@/lib/utils";

type StackDotColor = "default" | "accent" | "green";

interface StackDotProps {
  color?: StackDotColor;
  isFirst?: boolean;
  isLast?: boolean;
}

const dotColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--fg-subtle)]",
  accent: "bg-[var(--accent)]",
  green: "bg-[var(--green)]",
};

const lineColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--border)]",
  accent: "bg-[var(--border)]",
  green: "bg-[var(--border)]",
};

function StackDot({ color = "default", isFirst = false, isLast = false }: StackDotProps) {
  return (
    <div className="relative flex flex-col items-center w-4 self-stretch">
      {/* Line above the dot */}
      <div
        className={cn(
          "w-px flex-1",
          isFirst ? "bg-transparent" : lineColorMap[color]
        )}
      />
      {/* The dot */}
      <div
        className={cn(
          "w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-[var(--bg-surface)]",
          dotColorMap[color]
        )}
      />
      {/* Line below the dot */}
      <div
        className={cn(
          "w-px flex-1",
          isLast ? "bg-transparent" : lineColorMap[color]
        )}
      />
    </div>
  );
}

StackDot.displayName = "StackDot";

export { StackDot };
export type { StackDotProps, StackDotColor };

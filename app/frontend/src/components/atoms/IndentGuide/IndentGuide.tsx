import { cn } from "@/lib/utils";

interface IndentGuideProps {
  depth: number;
  className?: string;
}

function IndentGuide({ depth, className }: IndentGuideProps) {
  if (depth <= 0) return null;

  return (
    <span className={cn("absolute inset-y-0 left-0 pointer-events-none", className)}>
      {Array.from({ length: depth }, (_, i) => (
        <span
          key={i}
          className="absolute top-0 bottom-0 w-px bg-[var(--indent-guide)]"
          style={{ left: `${i * 12 + 8}px` }}
        />
      ))}
    </span>
  );
}

IndentGuide.displayName = "IndentGuide";

export { IndentGuide };
export type { IndentGuideProps };

import { cn } from "@/lib/utils";
import type { DiffLine as DiffLineType } from "@/types/diff";

interface DiffLineAtomProps {
  line: DiffLineType;
}

const bgMap: Record<DiffLineType["type"], string> = {
  add: "bg-[var(--green-bg)]",
  del: "bg-[var(--red-bg)]",
  context: "",
  hunk: "bg-[var(--accent-muted)]",
};

const prefixMap: Record<DiffLineType["type"], string> = {
  add: "+",
  del: "-",
  context: " ",
  hunk: "",
};

function DiffLineAtom({ line }: DiffLineAtomProps) {
  const isHunk = line.type === "hunk";

  return (
    <div
      className={cn(
        "flex font-[family-name:var(--font-mono)] text-xs leading-5 border-b border-[var(--border-muted)]/50",
        bgMap[line.type]
      )}
    >
      {/* Gutter: old line number */}
      <span
        className="w-[50px] shrink-0 text-right pr-2 pl-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/50"
        aria-hidden="true"
      >
        {line.old_num ?? ""}
      </span>

      {/* Gutter: new line number */}
      <span
        className="w-[50px] shrink-0 text-right pr-2 pl-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/50"
        aria-hidden="true"
      >
        {line.new_num ?? ""}
      </span>

      {/* Content */}
      <span
        className={cn(
          "flex-1 pl-2 pr-4 whitespace-pre",
          isHunk ? "text-[var(--fg-muted)] italic" : "text-[var(--fg-default)]"
        )}
      >
        {isHunk ? line.content : `${prefixMap[line.type]}${line.content}`}
      </span>
    </div>
  );
}

DiffLineAtom.displayName = "DiffLineAtom";

export { DiffLineAtom };
export type { DiffLineAtomProps };

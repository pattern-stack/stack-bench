import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";
import type { DiffLine as DiffLineType } from "@/types/diff";

interface DiffLineAtomProps {
  line: DiffLineType;
  highlightedHtml?: string;
  selected?: boolean;
  onSelect?: () => void;
  onAskAgent?: () => void;
  onAddComment?: () => void;
}

const bgMap: Record<DiffLineType["type"], string> = {
  add: "bg-[var(--green-bg)]",
  del: "bg-[var(--red-bg)]",
  context: "",
  hunk: "bg-[var(--accent-muted)]",
};

const selectedBgMap: Record<DiffLineType["type"], string> = {
  add: "bg-[var(--green-bg)]/80",
  del: "bg-[var(--red-bg)]/80",
  context: "bg-[var(--accent-muted)]/30",
  hunk: "bg-[var(--accent-muted)]",
};

const prefixMap: Record<DiffLineType["type"], string> = {
  add: "+",
  del: "-",
  context: " ",
  hunk: "",
};

function DiffLineAtom({
  line,
  highlightedHtml,
  selected = false,
  onSelect,
  onAskAgent,
  onAddComment,
}: DiffLineAtomProps) {
  const isHunk = line.type === "hunk";
  const isInteractive = !isHunk && onSelect;

  return (
    <div
      className={cn(
        "group/line relative flex font-[family-name:var(--font-mono)] text-xs leading-5 border-b border-[var(--border-muted)]/50",
        selected ? selectedBgMap[line.type] : bgMap[line.type],
        selected && "border-l-2 border-l-[var(--accent-emerald)]",
        isInteractive && "cursor-pointer"
      )}
      onClick={isInteractive ? onSelect : undefined}
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
        {isHunk ? (
          line.content
        ) : (
          <>
            {prefixMap[line.type]}
            {highlightedHtml ? (
              <span dangerouslySetInnerHTML={{ __html: highlightedHtml }} />
            ) : (
              line.content
            )}
          </>
        )}
      </span>

      {/* Hover actions */}
      {!isHunk && (onAskAgent || onAddComment) && (
        <div
          className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover/line:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          {onAskAgent && (
            <button
              type="button"
              className="flex items-center justify-center w-5 h-5 rounded text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--accent-muted)] transition-colors"
              onClick={onAskAgent}
              title="Ask agent"
            >
              <Icon name="sparkles" size="sm" />
            </button>
          )}
          {onAddComment && (
            <button
              type="button"
              className="flex items-center justify-center w-5 h-5 rounded text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--accent-muted)] transition-colors"
              onClick={onAddComment}
              title="Add comment"
            >
              <Icon name="message-square" size="sm" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

DiffLineAtom.displayName = "DiffLineAtom";

export { DiffLineAtom };
export type { DiffLineAtomProps };

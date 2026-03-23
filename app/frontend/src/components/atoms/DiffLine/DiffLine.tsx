import { cn } from "@/lib/utils";
import { Icon } from "@/components/atoms/Icon";
import type { DiffLine as DiffLineType } from "@/types/diff";

interface DiffLineAtomProps {
  line: DiffLineType;
  highlightedHtml?: string;
  selected?: boolean;
  rangeSelected?: boolean;
  hasComment?: boolean;
  onSelect?: () => void;
  onAskAgent?: () => void;
  onAddComment?: () => void;
  onMouseDown?: () => void;
  onMouseEnter?: () => void;
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
  rangeSelected = false,
  hasComment = false,
  onSelect,
  onAskAgent,
  onAddComment,
  onMouseDown,
  onMouseEnter,
}: DiffLineAtomProps) {
  const isHunk = line.type === "hunk";
  const isInteractive = !isHunk && onSelect;

  return (
    <div
      className={cn(
        "group/line relative flex font-[family-name:var(--font-mono)] text-xs leading-5 select-none",
        rangeSelected
          ? "bg-[var(--accent-muted)]/50"
          : selected
            ? selectedBgMap[line.type]
            : bgMap[line.type],
        selected && !rangeSelected && "border-l-2 border-l-[var(--accent-emerald)]",
        isInteractive && "cursor-pointer"
      )}
      onClick={isInteractive ? onSelect : undefined}
      onMouseDown={onMouseDown}
      onMouseEnter={onMouseEnter}
    >
      {/* Gutter: old line number */}
      <span
        className="w-[40px] shrink-0 text-right pr-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/30"
        aria-hidden="true"
      >
        {line.old_num ?? ""}
      </span>

      {/* Gutter: new line number */}
      <span
        className="w-[40px] shrink-0 text-right pr-2 select-none text-[var(--fg-subtle)] border-r border-[var(--border-muted)]/30"
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

      {/* Right-side actions */}
      {!isHunk && (onAddComment || onAskAgent) && (
        <div
          className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5"
          onClick={(e) => e.stopPropagation()}
        >
          {onAskAgent && (
            <button
              type="button"
              className="flex items-center justify-center w-5 h-5 rounded text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--accent-muted)] transition-colors opacity-0 group-hover/line:opacity-100 cursor-pointer"
              onClick={onAskAgent}
              title="Ask agent"
            >
              <Icon name="sparkles" size="sm" />
            </button>
          )}
          {onAddComment && (
            <button
              type="button"
              className={cn(
                "flex items-center justify-center w-6 h-6 rounded-full transition-all cursor-pointer",
                hasComment
                  ? "opacity-100 bg-[var(--accent)] text-white"
                  : "opacity-0 group-hover/line:opacity-100 bg-[var(--accent)] text-white hover:brightness-110 hover:scale-110"
              )}
              onClick={onAddComment}
              title={hasComment ? "View comments" : "Add comment"}
            >
              <Icon name={hasComment ? "message-square" : "plus"} size="xs" />
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

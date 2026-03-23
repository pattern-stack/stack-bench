import { useRef } from "react";
import { DiffLineAtom } from "@/components/atoms/DiffLine";
import { CommentPopover } from "@/components/molecules/CommentPopover";
import { Icon } from "@/components/atoms/Icon";
import type { ReviewComment } from "@/hooks/useReviewComments";
import type { DiffHunk as DiffHunkType } from "@/types/diff";

interface DiffHunkMoleculeProps {
  hunk: DiffHunkType;
  filePath: string;
  selectedLines?: Set<string>;
  onLineSelect?: (lineKey: string) => void;
  onAskAgent?: (lineKey: string) => void;
  onAddComment?: (lineKey: string) => void;
  commentsByLine?: Map<string, ReviewComment[]>;
  commentingLine?: string | null;
  onSubmitComment?: (lineKey: string, body: string) => void;
  onCancelComment?: () => void;
  rangeSelectedLines?: Set<string>;
  rangeLineCount?: number;
  onRangeMouseDown?: (lineKey: string, lineIndex: number) => void;
  onRangeMouseEnter?: (lineKey: string, lineIndex: number) => void;
}

function makeLineKey(filePath: string, line: { type: string; old_num: number | null; new_num: number | null }): string {
  return `${filePath}:${line.type}:${line.old_num ?? ""}:${line.new_num ?? ""}`;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function CommentThread({ comments }: { comments: ReviewComment[] }) {
  return (
    <div className="mx-4 my-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden shadow-sm shadow-black/10">
      {comments.map((comment, i) => (
        <div
          key={comment.id}
          className={i > 0 ? "border-t border-[var(--border-muted)]" : ""}
        >
          <div className="flex items-start gap-2.5 px-3 py-2.5">
            <div className="w-5 h-5 rounded-full bg-[var(--accent-muted)] flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px] text-[var(--accent)] font-medium">
                {comment.author.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-medium text-[var(--fg-default)]">
                  {comment.author}
                </span>
                <span className="text-[10px] text-[var(--fg-subtle)]">
                  {timeAgo(comment.created_at)}
                </span>
              </div>
              <p className="text-xs text-[var(--fg-muted)] leading-relaxed whitespace-pre-wrap">
                {comment.body}
              </p>
            </div>
            {comment.resolved && (
              <Icon name="check" size="xs" className="text-[var(--green)] shrink-0 mt-1" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function DiffLineWithRef({
  lineKey,
  line,
  hunkLine,
  selectedLines,
  rangeSelectedLines,
  commentsByLine,
  commentingLine,
  rangeLineCount,
  onLineSelect,
  onAskAgent,
  onAddComment,
  onSubmitComment,
  onCancelComment,
  onRangeMouseDown,
  onRangeMouseEnter,
  lineIndex,
}: {
  lineKey: string;
  line: DiffHunkType["lines"][number];
  hunkLine: DiffHunkType["lines"][number];
  selectedLines?: Set<string>;
  rangeSelectedLines?: Set<string>;
  commentsByLine?: Map<string, ReviewComment[]>;
  commentingLine?: string | null;
  rangeLineCount?: number;
  onLineSelect?: (lineKey: string) => void;
  onAskAgent?: (lineKey: string) => void;
  onAddComment?: (lineKey: string) => void;
  onSubmitComment?: (lineKey: string, body: string) => void;
  onCancelComment?: () => void;
  onRangeMouseDown?: (lineKey: string, lineIndex: number) => void;
  onRangeMouseEnter?: (lineKey: string, lineIndex: number) => void;
  lineIndex: number;
}) {
  const lineRef = useRef<HTMLDivElement>(null);
  const lineComments = commentsByLine?.get(lineKey);
  const isCommenting = commentingLine === lineKey;
  const hasComment = (lineComments && lineComments.length > 0) || false;

  return (
    <div ref={lineRef}>
      <DiffLineAtom
        line={hunkLine}
        highlightedHtml={line.highlightedHtml}
        selected={selectedLines?.has(lineKey)}
        rangeSelected={rangeSelectedLines?.has(lineKey)}
        hasComment={hasComment}
        onSelect={onLineSelect ? () => onLineSelect(lineKey) : undefined}
        onAskAgent={onAskAgent ? () => onAskAgent(lineKey) : undefined}
        onAddComment={onAddComment ? () => onAddComment(lineKey) : undefined}
        onMouseDown={onRangeMouseDown && hunkLine.type !== "hunk" ? () => onRangeMouseDown(lineKey, lineIndex) : undefined}
        onMouseEnter={onRangeMouseEnter && hunkLine.type !== "hunk" ? () => onRangeMouseEnter(lineKey, lineIndex) : undefined}
      />

      {/* Existing comments — inline thread */}
      {hasComment && <CommentThread comments={lineComments!} />}

      {/* Comment popover — floats over the diff */}
      {isCommenting && onSubmitComment && onCancelComment && (
        <CommentPopover
          anchorRef={lineRef}
          onSubmit={(body) => onSubmitComment(lineKey, body)}
          onCancel={onCancelComment}
          lineCount={rangeLineCount}
        />
      )}
    </div>
  );
}

function DiffHunkMolecule({
  hunk,
  filePath,
  selectedLines,
  onLineSelect,
  onAskAgent,
  onAddComment,
  commentsByLine,
  commentingLine,
  onSubmitComment,
  onCancelComment,
  rangeSelectedLines,
  rangeLineCount,
  onRangeMouseDown,
  onRangeMouseEnter,
}: DiffHunkMoleculeProps) {
  return (
    <div>
      {/* Hunk header */}
      <DiffLineAtom
        line={{
          type: "hunk",
          old_num: null,
          new_num: null,
          content: hunk.header,
        }}
      />

      {/* Hunk lines */}
      {hunk.lines.map((line, i) => {
        const lineKey = makeLineKey(filePath, line);

        return (
          <DiffLineWithRef
            key={i}
            lineKey={lineKey}
            line={line}
            hunkLine={line}
            selectedLines={selectedLines}
            rangeSelectedLines={rangeSelectedLines}
            commentsByLine={commentsByLine}
            commentingLine={commentingLine}
            rangeLineCount={rangeLineCount}
            onLineSelect={onLineSelect}
            onAskAgent={onAskAgent}
            onAddComment={onAddComment}
            onSubmitComment={onSubmitComment}
            onCancelComment={onCancelComment}
            onRangeMouseDown={onRangeMouseDown}
            onRangeMouseEnter={onRangeMouseEnter}
            lineIndex={i}
          />
        );
      })}
    </div>
  );
}

DiffHunkMolecule.displayName = "DiffHunkMolecule";

export { DiffHunkMolecule };
export type { DiffHunkMoleculeProps };

import { useRef } from "react";
import { DiffLineAtom } from "@/components/atoms/DiffLine";
import { CommentPopover } from "@/components/molecules/CommentPopover";
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

function DiffLineWithRef({
  lineKey,
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
        highlightedHtml={hunkLine.highlightedHtml}
        selected={selectedLines?.has(lineKey)}
        rangeSelected={rangeSelectedLines?.has(lineKey)}
        hasComment={hasComment}
        onSelect={onLineSelect ? () => onLineSelect(lineKey) : undefined}
        onAskAgent={onAskAgent ? () => onAskAgent(lineKey) : undefined}
        onAddComment={onAddComment ? () => onAddComment(lineKey) : undefined}
        onMouseDown={onRangeMouseDown && hunkLine.type !== "hunk" ? () => onRangeMouseDown(lineKey, lineIndex) : undefined}
        onMouseEnter={onRangeMouseEnter && hunkLine.type !== "hunk" ? () => onRangeMouseEnter(lineKey, lineIndex) : undefined}
      />

      {/* Floating popover for both new comments and existing threads */}
      {isCommenting && onSubmitComment && onCancelComment && (
        <CommentPopover
          anchorRef={lineRef}
          onSubmit={(body) => onSubmitComment(lineKey, body)}
          onCancel={onCancelComment}
          lineCount={rangeLineCount}
          existingComments={lineComments}
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

import { DiffLineAtom } from "@/components/atoms/DiffLine";
import { CommentInput } from "@/components/molecules/CommentInput";
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
}

function makeLineKey(filePath: string, line: { type: string; old_num: number | null; new_num: number | null }): string {
  return `${filePath}:${line.type}:${line.old_num ?? ""}:${line.new_num ?? ""}`;
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
        const lineComments = commentsByLine?.get(lineKey);
        const isCommenting = commentingLine === lineKey;

        return (
          <div key={i}>
            <DiffLineAtom
              line={line}
              highlightedHtml={line.highlightedHtml}
              selected={selectedLines?.has(lineKey)}
              onSelect={onLineSelect ? () => onLineSelect(lineKey) : undefined}
              onAskAgent={onAskAgent ? () => onAskAgent(lineKey) : undefined}
              onAddComment={onAddComment ? () => onAddComment(lineKey) : undefined}
            />

            {/* Existing comments */}
            {lineComments && lineComments.length > 0 && (
              <div className="border-y border-[var(--border)]">
                {lineComments.map((comment) => (
                  <div
                    key={comment.id}
                    className="flex gap-2 px-4 py-2 bg-[var(--bg-sunken)] text-sm"
                  >
                    <span className="text-[var(--fg-muted)] shrink-0">{comment.author}:</span>
                    <span className="text-[var(--fg)]">{comment.body}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Comment input */}
            {isCommenting && onSubmitComment && onCancelComment && (
              <CommentInput
                onSubmit={(body) => onSubmitComment(lineKey, body)}
                onCancel={onCancelComment}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

DiffHunkMolecule.displayName = "DiffHunkMolecule";

export { DiffHunkMolecule };
export type { DiffHunkMoleculeProps };

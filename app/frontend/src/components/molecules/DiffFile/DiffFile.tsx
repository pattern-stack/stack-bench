import { useState, useEffect } from "react";
import { DiffFileHeader } from "@/components/molecules/DiffFileHeader";
import { DiffHunkMolecule } from "@/components/molecules/DiffHunk";
import { useHighlightedDiff } from "@/hooks/useHighlightedDiff";
import type { ReviewComment } from "@/hooks/useReviewComments";
import type { DiffFile as DiffFileType } from "@/types/diff";

interface DiffFileMoleculeProps {
  file: DiffFileType;
  viewed?: boolean;
  onViewedChange?: (viewed: boolean) => void;
  selectedLines?: Set<string>;
  onLineSelect?: (lineKey: string) => void;
  onAskAgent?: (lineKey: string) => void;
  onAddComment?: (lineKey: string) => void;
  commentsByLine?: Map<string, ReviewComment[]>;
  commentingLine?: string | null;
  onSubmitComment?: (lineKey: string, body: string) => void;
  onCancelComment?: () => void;
  forceExpanded?: boolean | null;
  defaultExpanded?: boolean;
  rangeSelectedLines?: Set<string>;
  onRangeMouseDown?: (lineKey: string, lineIndex: number) => void;
  onRangeMouseEnter?: (lineKey: string, lineIndex: number) => void;
}

function DiffFileMolecule({
  file,
  viewed = false,
  onViewedChange,
  selectedLines,
  onLineSelect,
  onAskAgent,
  onAddComment,
  commentsByLine,
  commentingLine,
  onSubmitComment,
  onCancelComment,
  forceExpanded = null,
  defaultExpanded = true,
  rangeSelectedLines,
  onRangeMouseDown,
  onRangeMouseEnter,
}: DiffFileMoleculeProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  useEffect(() => {
    if (forceExpanded !== null) setExpanded(forceExpanded);
  }, [forceExpanded]);
  const { highlightedHunks } = useHighlightedDiff(file, expanded);

  return (
    <div>
      <DiffFileHeader
        file={file}
        expanded={expanded}
        viewed={viewed}
        onToggle={() => setExpanded(!expanded)}
        onViewedChange={onViewedChange}
      />
      {expanded && (
        <div className="border-x border-b border-[var(--border)] rounded-b overflow-hidden">
          {highlightedHunks.map((hunk, i) => (
            <DiffHunkMolecule
              key={i}
              hunk={hunk}
              filePath={file.path}
              selectedLines={selectedLines}
              onLineSelect={onLineSelect}
              onAskAgent={onAskAgent}
              onAddComment={onAddComment}
              commentsByLine={commentsByLine}
              commentingLine={commentingLine}
              onSubmitComment={onSubmitComment}
              onCancelComment={onCancelComment}
              rangeSelectedLines={rangeSelectedLines}
              onRangeMouseDown={onRangeMouseDown}
              onRangeMouseEnter={onRangeMouseEnter}
            />
          ))}
        </div>
      )}
    </div>
  );
}

DiffFileMolecule.displayName = "DiffFileMolecule";

export { DiffFileMolecule };
export type { DiffFileMoleculeProps };

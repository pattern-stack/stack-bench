import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { DiffFileMolecule } from "@/components/molecules/DiffFile";
import { useReviewComments, useCreateComment } from "@/hooks/useReviewComments";
import type { ReviewComment } from "@/hooks/useReviewComments";
import type { DiffData } from "@/types/diff";

interface FilesChangedPanelProps {
  diffData: DiffData;
  forceExpanded?: boolean | null;
  stackId?: string;
  branchId?: string;
  pullRequestId?: string;
  floatingComments?: boolean;
}

function FilesChangedPanel({
  diffData,
  forceExpanded = null,
  stackId,
  branchId,
  pullRequestId,
  floatingComments: floatingCommentsProp = true,
}: FilesChangedPanelProps) {
  const [viewedFiles, setViewedFiles] = useState<Set<string>>(new Set());
  const [selectedLines, setSelectedLines] = useState<Set<string>>(new Set());
  const [commentingLine, setCommentingLine] = useState<string | null>(null);

  // Range selection state for click-drag
  const [rangeSelectedLines, setRangeSelectedLines] = useState<Set<string>>(new Set());
  const dragState = useRef<{
    active: boolean;
    startKey: string;
    startIndex: number;
    allKeys: string[];
  } | null>(null);

  const { data: comments } = useReviewComments(stackId, branchId);
  const createComment = useCreateComment(stackId, branchId);

  // Build ordered list of all line keys for range selection
  const allLineKeys = useMemo(() => {
    const keys: string[] = [];
    for (const file of diffData.files) {
      for (const hunk of file.hunks) {
        for (const line of hunk.lines) {
          if (line.type === "hunk") continue;
          keys.push(`${file.path}:${line.type}:${line.old_num ?? ""}:${line.new_num ?? ""}`);
        }
      }
    }
    return keys;
  }, [diffData]);

  // End drag on mouseup anywhere
  useEffect(() => {
    const handleMouseUp = () => {
      if (!dragState.current?.active) return;
      const range = rangeSelectedLines;
      dragState.current = null;
      if (range.size > 0) {
        // Open comment input at the last line of the range
        const lastKey = allLineKeys.filter(k => range.has(k)).pop();
        if (lastKey) setCommentingLine(lastKey);
      }
    };
    window.addEventListener("mouseup", handleMouseUp);
    return () => window.removeEventListener("mouseup", handleMouseUp);
  }, [rangeSelectedLines, allLineKeys]);

  // Build a Map<lineKey, ReviewComment[]> for efficient lookup
  const commentsByLine = useMemo(() => {
    const map = new Map<string, ReviewComment[]>();
    if (!comments) return map;
    for (const c of comments) {
      const existing = map.get(c.line_key) ?? [];
      existing.push(c);
      map.set(c.line_key, existing);
    }
    return map;
  }, [comments]);

  const handleViewedChange = useCallback((path: string, viewed: boolean) => {
    setViewedFiles((prev) => {
      const next = new Set(prev);
      if (viewed) next.add(path);
      else next.delete(path);
      return next;
    });
  }, []);

  const handleLineSelect = useCallback((lineKey: string) => {
    setSelectedLines((prev) => {
      const next = new Set(prev);
      if (next.has(lineKey)) next.delete(lineKey);
      else next.add(lineKey);
      return next;
    });
  }, []);

  const handleAskAgent = useCallback((_lineKey: string) => {
    // Stub — will be wired to agent panel
  }, []);

  const handleAddComment = useCallback((lineKey: string) => {
    setCommentingLine(lineKey);
  }, []);

  const handleSubmitComment = useCallback(
    (lineKey: string, body: string) => {
      if (!pullRequestId) return;

      // Parse lineKey: "filePath:type:old_num:new_num"
      const parts = lineKey.split(":");
      const path = parts.slice(0, -3).join(":");
      const lineType = parts[parts.length - 3];
      const oldNum = parts[parts.length - 2];
      const newNum = parts[parts.length - 1];

      const lineNumber = newNum ? parseInt(newNum, 10) : oldNum ? parseInt(oldNum, 10) : undefined;
      const side = lineType === "del" ? "LEFT" : "RIGHT";

      createComment.mutate({
        pull_request_id: pullRequestId,
        path,
        line_key: lineKey,
        body,
        author: "you",
        line_number: lineNumber ?? null,
        side,
      });

      setCommentingLine(null);
    },
    [pullRequestId, createComment]
  );

  const handleCancelComment = useCallback(() => {
    setCommentingLine(null);
    setRangeSelectedLines(new Set());
  }, []);

  const handleRangeMouseDown = useCallback(
    (lineKey: string, _lineIndex: number) => {
      const globalIndex = allLineKeys.indexOf(lineKey);
      if (globalIndex === -1) return;
      dragState.current = {
        active: true,
        startKey: lineKey,
        startIndex: globalIndex,
        allKeys: allLineKeys,
      };
      setRangeSelectedLines(new Set([lineKey]));
      setCommentingLine(null);
    },
    [allLineKeys]
  );

  const handleRangeMouseEnter = useCallback(
    (lineKey: string, _lineIndex: number) => {
      if (!dragState.current?.active) return;
      const globalIndex = allLineKeys.indexOf(lineKey);
      if (globalIndex === -1) return;
      const { startIndex } = dragState.current;
      const lo = Math.min(startIndex, globalIndex);
      const hi = Math.max(startIndex, globalIndex);
      setRangeSelectedLines(new Set(allLineKeys.slice(lo, hi + 1)));
    },
    [allLineKeys]
  );

  const manyFiles = diffData.files.length > 5;

  if (diffData.files.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[var(--fg-muted)] text-sm">No files changed</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {diffData.files.map((file, index) => (
        <DiffFileMolecule
          key={file.path}
          file={file}
          viewed={viewedFiles.has(file.path)}
          onViewedChange={(v) => handleViewedChange(file.path, v)}
          selectedLines={selectedLines}
          onLineSelect={handleLineSelect}
          onAskAgent={handleAskAgent}
          onAddComment={handleAddComment}
          commentsByLine={commentsByLine}
          commentingLine={commentingLine}
          onSubmitComment={handleSubmitComment}
          onCancelComment={handleCancelComment}
          rangeSelectedLines={rangeSelectedLines}
          rangeLineCount={rangeSelectedLines.size}
          onRangeMouseDown={handleRangeMouseDown}
          onRangeMouseEnter={handleRangeMouseEnter}
          floatingComments={floatingCommentsProp}
          forceExpanded={forceExpanded}
          defaultExpanded={manyFiles ? index === 0 : true}
        />
      ))}
    </div>
  );
}

FilesChangedPanel.displayName = "FilesChangedPanel";

export { FilesChangedPanel };
export type { FilesChangedPanelProps };

import { useState, useCallback, useMemo } from "react";
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
}

function FilesChangedPanel({
  diffData,
  forceExpanded = null,
  stackId,
  branchId,
  pullRequestId,
}: FilesChangedPanelProps) {
  const [viewedFiles, setViewedFiles] = useState<Set<string>>(new Set());
  const [selectedLines, setSelectedLines] = useState<Set<string>>(new Set());
  const [commentingLine, setCommentingLine] = useState<string | null>(null);

  const { data: comments } = useReviewComments(stackId, branchId);
  const createComment = useCreateComment(stackId, branchId);

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
  }, []);

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

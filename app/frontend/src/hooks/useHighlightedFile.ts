import { useState, useEffect, useMemo } from "react";
import type { FileContent } from "@/types/file-tree";
import { langFromPath } from "@/lib/lang-from-path";
import { highlightCode } from "@/lib/shiki";

const MAX_HIGHLIGHT_LINES = 5000;

export function useHighlightedFile(file: FileContent | null): {
  highlightedLines: string[];
  loading: boolean;
} {
  const lang = useMemo(
    () => (file ? langFromPath(file.path) : undefined),
    [file?.path]
  );

  const [highlightedLines, setHighlightedLines] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const contentKey = useMemo(() => {
    if (!file || !lang) return null;
    if (file.lines > MAX_HIGHLIGHT_LINES) return null;
    return file.content;
  }, [file?.content, lang, file?.lines]);

  useEffect(() => {
    if (!contentKey || !lang) {
      setHighlightedLines([]);
      return;
    }

    let cancelled = false;
    setLoading(true);

    highlightCode(contentKey, lang)
      .then((lines) => {
        if (!cancelled) {
          setHighlightedLines(lines);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHighlightedLines([]);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [contentKey, lang]);

  return { highlightedLines, loading };
}

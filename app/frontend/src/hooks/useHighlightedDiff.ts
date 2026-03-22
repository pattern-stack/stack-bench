import { useState, useEffect, useMemo } from "react";
import type { DiffFile, DiffHunk, DiffLine } from "@/types/diff";
import { langFromPath } from "@/lib/lang-from-path";
import { highlightCode } from "@/lib/shiki";

export function useHighlightedDiff(
  file: DiffFile,
  enabled: boolean
): { highlightedHunks: DiffHunk[] } {
  const lang = useMemo(() => langFromPath(file.path), [file.path]);

  const [highlightedLines, setHighlightedLines] = useState<Map<string, string>>(
    new Map()
  );

  // Build a stable key for memoization
  const contentKey = useMemo(() => {
    if (!lang || !enabled) return null;
    return file.hunks
      .flatMap((h) => h.lines.map((l) => l.content))
      .join("\n");
  }, [file.hunks, lang, enabled]);

  useEffect(() => {
    if (!lang || !enabled || contentKey === null) return;

    let cancelled = false;

    async function highlight() {
      // Reassemble old file (context + del lines) and new file (context + add lines)
      const oldLines: { content: string; key: string }[] = [];
      const newLines: { content: string; key: string }[] = [];

      file.hunks.forEach((hunk, hi) => {
        hunk.lines.forEach((line, li) => {
          const key = `${hi}-${li}`;
          if (line.type === "context") {
            oldLines.push({ content: line.content, key });
            newLines.push({ content: line.content, key });
          } else if (line.type === "del") {
            oldLines.push({ content: line.content, key });
          } else if (line.type === "add") {
            newLines.push({ content: line.content, key });
          }
        });
      });

      try {
        const [oldHighlighted, newHighlighted] = await Promise.all([
          highlightCode(
            oldLines.map((l) => l.content).join("\n"),
            lang!
          ),
          highlightCode(
            newLines.map((l) => l.content).join("\n"),
            lang!
          ),
        ]);

        if (cancelled) return;

        const map = new Map<string, string>();

        // For context lines, both old and new produce the same highlight.
        // We use the "new" version for context lines since it's the same content.
        oldLines.forEach((entry, i) => {
          if (oldHighlighted[i] !== undefined) {
            // Only set if not already set (context lines will be set by newLines too)
            if (!map.has(entry.key)) {
              map.set(entry.key, oldHighlighted[i]);
            }
          }
        });

        newLines.forEach((entry, i) => {
          if (newHighlighted[i] !== undefined) {
            map.set(entry.key, newHighlighted[i]);
          }
        });

        setHighlightedLines(map);
      } catch {
        // Silently skip highlighting on error
      }
    }

    highlight();

    return () => {
      cancelled = true;
    };
  }, [contentKey, lang, enabled, file.hunks]);

  const highlightedHunks = useMemo(() => {
    if (highlightedLines.size === 0) return file.hunks;

    return file.hunks.map((hunk, hi): DiffHunk => ({
      ...hunk,
      lines: hunk.lines.map((line, li): DiffLine => {
        if (line.type === "hunk") return line;
        const key = `${hi}-${li}`;
        const html = highlightedLines.get(key);
        if (html) {
          return { ...line, highlightedHtml: html };
        }
        return line;
      }),
    }));
  }, [file.hunks, highlightedLines]);

  return { highlightedHunks };
}

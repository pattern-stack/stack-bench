import { DiffLineAtom } from "@/components/atoms/DiffLine";
import type { DiffHunk as DiffHunkType } from "@/types/diff";

interface DiffHunkMoleculeProps {
  hunk: DiffHunkType;
  filePath: string;
  selectedLines?: Set<string>;
  onLineSelect?: (lineKey: string) => void;
  onAskAgent?: (lineKey: string) => void;
  onAddComment?: (lineKey: string) => void;
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
          <DiffLineAtom
            key={i}
            line={line}
            highlightedHtml={line.highlightedHtml}
            selected={selectedLines?.has(lineKey)}
            onSelect={onLineSelect ? () => onLineSelect(lineKey) : undefined}
            onAskAgent={onAskAgent ? () => onAskAgent(lineKey) : undefined}
            onAddComment={onAddComment ? () => onAddComment(lineKey) : undefined}
          />
        );
      })}
    </div>
  );
}

DiffHunkMolecule.displayName = "DiffHunkMolecule";

export { DiffHunkMolecule };
export type { DiffHunkMoleculeProps };

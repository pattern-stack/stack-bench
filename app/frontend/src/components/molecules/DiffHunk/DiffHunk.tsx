import { DiffLineAtom } from "@/components/atoms/DiffLine";
import type { DiffHunk as DiffHunkType } from "@/types/diff";

interface DiffHunkMoleculeProps {
  hunk: DiffHunkType;
}

function DiffHunkMolecule({ hunk }: DiffHunkMoleculeProps) {
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
      {hunk.lines.map((line, i) => (
        <DiffLineAtom key={i} line={line} highlightedHtml={line.highlightedHtml} />
      ))}
    </div>
  );
}

DiffHunkMolecule.displayName = "DiffHunkMolecule";

export { DiffHunkMolecule };
export type { DiffHunkMoleculeProps };

import { useState } from "react";
import { DiffFileHeader } from "@/components/molecules/DiffFileHeader";
import { DiffHunkMolecule } from "@/components/molecules/DiffHunk";
import { useHighlightedDiff } from "@/hooks/useHighlightedDiff";
import type { DiffFile as DiffFileType } from "@/types/diff";

interface DiffFileMoleculeProps {
  file: DiffFileType;
  viewed?: boolean;
  onViewedChange?: (viewed: boolean) => void;
}

function DiffFileMolecule({ file, viewed = false, onViewedChange }: DiffFileMoleculeProps) {
  const [expanded, setExpanded] = useState(true);
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
            <DiffHunkMolecule key={i} hunk={hunk} />
          ))}
        </div>
      )}
    </div>
  );
}

DiffFileMolecule.displayName = "DiffFileMolecule";

export { DiffFileMolecule };
export type { DiffFileMoleculeProps };

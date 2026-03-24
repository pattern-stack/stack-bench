import { useState } from "react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/atoms/Collapsible";
import { DiffFileHeader } from "@/components/molecules/DiffFileHeader";
import { DiffHunkMolecule } from "@/components/molecules/DiffHunk";
import type { DiffFile as DiffFileType } from "@/types/diff";

interface DiffFileMoleculeProps {
  file: DiffFileType;
}

function DiffFileMolecule({ file }: DiffFileMoleculeProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <CollapsibleTrigger asChild>
        <DiffFileHeader
          file={file}
          expanded={expanded}
          onToggle={() => setExpanded(!expanded)}
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="border-x border-b border-[var(--border)] rounded-b overflow-hidden">
          {file.hunks.map((hunk, i) => (
            <DiffHunkMolecule key={i} hunk={hunk} />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

DiffFileMolecule.displayName = "DiffFileMolecule";

export { DiffFileMolecule };
export type { DiffFileMoleculeProps };

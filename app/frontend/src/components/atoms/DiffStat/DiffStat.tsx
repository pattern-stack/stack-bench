interface DiffStatProps {
  additions: number;
  deletions: number;
}

function DiffStat({ additions, deletions }: DiffStatProps) {
  if (additions === 0 && deletions === 0) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-xs">
      {additions > 0 && (
        <span className="text-[var(--green)]">+{additions}</span>
      )}
      {deletions > 0 && (
        <span className="text-[var(--red)]">-{deletions}</span>
      )}
    </span>
  );
}

DiffStat.displayName = "DiffStat";

export { DiffStat };
export type { DiffStatProps };

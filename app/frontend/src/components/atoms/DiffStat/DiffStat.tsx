interface DiffStatProps {
  additions: number;
  deletions: number;
}

function DiffStat({ additions, deletions }: DiffStatProps) {
  if (additions === 0 && deletions === 0) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-0.5 font-[family-name:var(--font-mono)] text-xs tabular-nums">
      <span className="text-[var(--green)] w-8 text-right">+{additions}</span>
      <span className="text-[var(--red)] w-8 text-right">-{deletions}</span>
    </span>
  );
}

DiffStat.displayName = "DiffStat";

export { DiffStat };
export type { DiffStatProps };

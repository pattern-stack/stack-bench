import type { DiffFile } from "@/types/diff";

interface DiffBadgeProps {
  changeType: DiffFile["change_type"];
}

const badgeConfig: Record<
  DiffFile["change_type"],
  { letter: string; bg: string; fg: string }
> = {
  added: { letter: "A", bg: "bg-[var(--green-bg)]", fg: "text-[var(--green)]" },
  modified: { letter: "M", bg: "bg-[var(--yellow)]/10", fg: "text-[var(--yellow)]" },
  deleted: { letter: "D", bg: "bg-[var(--red-bg)]", fg: "text-[var(--red)]" },
  renamed: { letter: "R", bg: "bg-[var(--purple)]/10", fg: "text-[var(--purple)]" },
};

function DiffBadge({ changeType }: DiffBadgeProps) {
  const config = badgeConfig[changeType];

  return (
    <span
      className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold leading-none ${config.bg} ${config.fg}`}
    >
      {config.letter}
    </span>
  );
}

DiffBadge.displayName = "DiffBadge";

export { DiffBadge };
export type { DiffBadgeProps };

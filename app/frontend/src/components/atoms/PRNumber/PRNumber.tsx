interface PRNumberProps {
  number: number;
}

function PRNumber({ number }: PRNumberProps) {
  return (
    <span className="text-xs text-[var(--fg-muted)] font-[family-name:var(--font-mono)]">
      #{number}
    </span>
  );
}

PRNumber.displayName = "PRNumber";

export { PRNumber };
export type { PRNumberProps };

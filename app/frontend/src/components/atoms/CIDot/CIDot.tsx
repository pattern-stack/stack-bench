import type { CIStatus } from "@/types/activity";

interface CIDotProps {
  status: CIStatus;
}

const colorMap: Record<Exclude<CIStatus, "none">, string> = {
  pass: "var(--green)",
  fail: "var(--red)",
  pending: "var(--yellow)",
};

const titleMap: Record<Exclude<CIStatus, "none">, string> = {
  pass: "CI: passing",
  fail: "CI: failing",
  pending: "CI: pending",
};

function CIDot({ status }: CIDotProps) {
  if (status === "none") return null;

  return (
    <span
      className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
      style={{ backgroundColor: colorMap[status] }}
      title={titleMap[status]}
    />
  );
}

CIDot.displayName = "CIDot";

export { CIDot };
export type { CIDotProps };

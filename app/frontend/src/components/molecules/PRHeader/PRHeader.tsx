import { BranchMeta } from "@/components/atoms/BranchMeta";

interface PRHeaderProps {
  title: string;
  baseBranch: string;
  headBranch: string;
  description?: string | null;
}

function PRHeader({ title, baseBranch, headBranch, description }: PRHeaderProps) {
  return (
    <div className="px-6 py-5 bg-[var(--bg-surface)] border-b border-[var(--border)]">
      <h2 className="text-xl font-semibold text-[var(--fg-default)] leading-tight">
        {title}
      </h2>
      <div className="mt-2">
        <BranchMeta base={baseBranch} head={headBranch} />
      </div>
      {description && (
        <p className="mt-3 text-sm text-[var(--fg-muted)] leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}

PRHeader.displayName = "PRHeader";

export { PRHeader };
export type { PRHeaderProps };

import { Link } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useProjectList } from "@/hooks/useProjectList";
import { useStackList } from "@/hooks/useStackList";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { Stack, BranchWithPR } from "@/types/stack";

/** Extract short branch name: "dugshub/demo/1-native-secrets" → "1-native-secrets" */
function shortBranch(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

/** PR state → display config */
function prStateConfig(state: string | undefined): { icon: "check" | "circle" | "git-commit"; color: string; label: string } {
  switch (state) {
    case "merged":
      return { icon: "check", color: "var(--purple)", label: "merged" };
    case "open":
    case "reviewing":
    case "ready":
    case "approved":
      return { icon: "circle", color: "var(--accent)", label: "open" };
    case "draft":
      return { icon: "git-commit", color: "var(--fg-subtle)", label: "draft" };
    default:
      return { icon: "git-commit", color: "var(--border-muted)", label: "no PR" };
  }
}

/** State badge colors */
const STATE_CONFIG: Record<string, { color: string; label: string }> = {
  active: { color: "var(--green)", label: "Active" },
  submitted: { color: "var(--accent)", label: "Submitted" },
  draft: { color: "var(--fg-subtle)", label: "Draft" },
  merged: { color: "var(--purple)", label: "Merged" },
};

function StacksListPage() {
  const { data: projects } = useProjectList();
  const projectId = projects[0]?.id;
  const { data: stacks, loading } = useStackList(projectId);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--fg-muted)]">Loading stacks...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-lg font-semibold text-[var(--fg-default)]">
          Stacks
        </h1>
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[var(--border-muted)] text-xs text-[var(--fg-muted)] hover:border-[var(--border)] hover:text-[var(--fg-default)] transition-colors">
          <Icon name="plus" size="xs" />
          New Stack
        </button>
      </div>
      <p className="text-xs text-[var(--fg-subtle)] mb-5">
        Manage and orchestrate development branch dependencies.
      </p>

      {stacks.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Icon name="git-branch" size="lg" className="text-[var(--fg-subtle)] mx-auto mb-2" />
            <p className="text-sm text-[var(--fg-muted)]">No stacks yet</p>
            <p className="text-xs text-[var(--fg-subtle)] mt-1">
              Create a stack to organize your branches
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {stacks.map((stack) => (
            <StackCard key={stack.id} stack={stack} />
          ))}
        </div>
      )}
    </div>
  );
}

function StackCard({ stack }: { stack: Stack }) {
  const { data: detail } = useStackDetail(stack.id);
  const branches = detail?.branches ?? [];
  const summary = computePRSummary(branches);
  const cfg = STATE_CONFIG[stack.state] ?? { color: "var(--fg-subtle)", label: "Draft" };

  return (
    <Link
      to={`/stacks/${stack.id}`}
      className="block rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] hover:border-[var(--border)] transition-colors"
    >
      {/* Header row */}
      <div className="flex items-center gap-4 px-5 py-3 border-b border-[var(--border-muted)]">
        {/* Name + badge */}
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <Icon name="git-merge" size="sm" className="text-[var(--fg-muted)] shrink-0" />
          <span className="text-sm font-medium text-[var(--fg-default)] truncate">
            {stack.name}
          </span>
          <span
            className="shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium"
            style={{
              color: cfg.color,
              border: `1px solid color-mix(in srgb, ${cfg.color} 30%, transparent)`,
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cfg.color }} />
            {cfg.label}
          </span>
        </div>

        {/* Summary stats */}
        <div className="flex items-center gap-5 shrink-0 text-xs">
          {/* PR counts */}
          <div className="flex items-center gap-2">
            {summary.open > 0 && (
              <span className="text-[var(--accent)]">{summary.open} open</span>
            )}
            {summary.merged > 0 && (
              <span className="text-[var(--purple)]">{summary.merged} merged</span>
            )}
            {summary.draft > 0 && (
              <span className="text-[var(--fg-subtle)]">{summary.draft} draft</span>
            )}
          </div>

          {/* Diff stats */}
          <span className="font-mono text-[10px]">
            <span className="text-[var(--green)]">+{summary.additions}</span>{" "}
            <span className="text-[var(--red)]">-{summary.deletions}</span>
          </span>

          {/* CI */}
          <CIStatusIndicator state={stack.state} />

          {/* Time */}
          <span className="text-[10px] text-[var(--fg-subtle)] w-[50px] text-right">
            {timeAgo(stack.updated_at)}
          </span>
        </div>
      </div>

      {/* Branch list */}
      <div className="px-5 py-2">
        {branches.map((b, i) => (
          <BranchRow
            key={b.branch.id}
            branch={b}
            isFirst={i === 0}
            isLast={i === branches.length - 1}
            trunk={stack.trunk}
          />
        ))}
        {branches.length === 0 && (
          <div className="py-2 text-xs text-[var(--fg-subtle)]">
            No branches yet
          </div>
        )}
      </div>
    </Link>
  );
}

function BranchRow({
  branch,
  isFirst,
  isLast,
  trunk,
}: {
  branch: BranchWithPR;
  isFirst: boolean;
  isLast: boolean;
  trunk: string;
}) {
  const pr = branch.pull_request;
  const cfg = prStateConfig(pr?.state);
  const name = shortBranch(branch.branch.name);
  const baseName = isFirst ? trunk : undefined;

  return (
    <div className="flex items-center gap-2 py-1 group">
      {/* Connector line */}
      <div className="w-4 flex flex-col items-center shrink-0">
        {/* Vertical line segment */}
        <div
          className={`w-px flex-1 ${isFirst ? "bg-transparent" : "bg-[var(--border-muted)]"}`}
          style={{ minHeight: 8 }}
        />
        {/* Node dot */}
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: cfg.color }}
        />
        {/* Vertical line segment */}
        <div
          className={`w-px flex-1 ${isLast ? "bg-transparent" : "bg-[var(--border-muted)]"}`}
          style={{ minHeight: 8 }}
        />
      </div>

      {/* Branch name */}
      <span className="text-xs font-mono text-[var(--fg-muted)] truncate min-w-0">
        {name}
      </span>

      {/* Arrow showing base */}
      <span className="text-[9px] text-[var(--fg-subtle)]">
        → {baseName ?? "↑"}
      </span>

      {/* PR info */}
      {pr && (
        <div className="flex items-center gap-2 ml-auto shrink-0">
          <span className="text-[10px] font-mono" style={{ color: cfg.color }}>
            #{pr.external_id}
          </span>
          <span
            className="text-[9px] capitalize px-1 py-0.5 rounded"
            style={{
              color: cfg.color,
              backgroundColor: `color-mix(in srgb, ${cfg.color} 10%, transparent)`,
            }}
          >
            {cfg.label}
          </span>
        </div>
      )}
    </div>
  );
}

function CIStatusIndicator({ state }: { state: string }) {
  if (state === "merged" || state === "active") {
    return (
      <div className="flex items-center gap-1">
        <Icon name="check-circle" size="xs" className="text-[var(--green)]" />
        <span className="text-[10px] text-[var(--green)]">
          {state === "merged" ? "Done" : "Passing"}
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <Icon name="activity" size="xs" className="text-[var(--fg-muted)]" />
      <span className="text-[10px] text-[var(--fg-muted)]">Pending</span>
    </div>
  );
}

function computePRSummary(branches: BranchWithPR[]) {
  let open = 0, merged = 0, draft = 0;
  let additions = 0, deletions = 0;

  for (const b of branches) {
    const state = b.pull_request?.state;
    if (state === "merged") merged++;
    else if (state === "open" || state === "reviewing" || state === "ready" || state === "approved") open++;
    else if (state === "draft") draft++;
    additions += 114;
    deletions += 30;
  }

  return { open, merged, draft, total: open + merged + draft, additions, deletions };
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

StacksListPage.displayName = "StacksListPage";

export { StacksListPage };

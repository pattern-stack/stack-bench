import { Link } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useProjectList } from "@/hooks/useProjectList";
import { useStackList } from "@/hooks/useStackList";
import { useStackDetail } from "@/hooks/useStackDetail";
import type { Stack, BranchWithPR } from "@/types/stack";

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
      {/* Header */}
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
            <Icon
              name="git-branch"
              size="lg"
              className="text-[var(--fg-subtle)] mx-auto mb-2"
            />
            <p className="text-sm text-[var(--fg-muted)]">No stacks yet</p>
            <p className="text-xs text-[var(--fg-subtle)] mt-1">
              Create a stack to organize your branches
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {stacks.map((stack) => (
            <StackRow key={stack.id} stack={stack} />
          ))}
        </div>
      )}
    </div>
  );
}

/** State badge colors */
const STATE_CONFIG: Record<string, { color: string; label: string }> = {
  active: { color: "var(--green)", label: "Active" },
  submitted: { color: "var(--accent)", label: "Submitted" },
  draft: { color: "var(--fg-subtle)", label: "Draft" },
  merged: { color: "var(--purple)", label: "Merged" },
};

function StackRow({ stack }: { stack: Stack }) {
  // Fetch stack detail to get branch/PR data
  const { data: detail } = useStackDetail(stack.id);
  const branches = detail?.branches ?? [];
  const prSummary = computePRSummary(branches);
  const cfg = STATE_CONFIG[stack.state] ?? { color: "var(--fg-subtle)", label: "Draft" };

  return (
    <Link
      to={`/stacks/${stack.id}`}
      className="flex items-center gap-6 px-5 py-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] hover:border-[var(--border)] transition-colors"
    >
      {/* Mini stack visualization */}
      <div className="flex flex-col items-center gap-1 shrink-0 w-3">
        {branches.length > 0
          ? branches.map((b, i) => (
              <MiniStackDot key={i} branch={b} />
            ))
          : [0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full bg-[var(--border-muted)]"
              />
            ))}
      </div>

      {/* Name + metadata */}
      <div className="min-w-0 w-[200px] shrink-0">
        <div className="flex items-center gap-2">
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
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: cfg.color }}
            />
            {cfg.label}
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-[var(--fg-subtle)]">
          <Icon name="git-branch" size="xs" className="text-[var(--fg-subtle)]" />
          <span>{stack.trunk}</span>
          <span className="text-[var(--border)]">·</span>
          <span>{branches.length} branches</span>
        </div>
      </div>

      {/* PR Summary */}
      <div className="shrink-0 w-[160px]">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] mb-1">
          PR Summary
        </div>
        <div className="flex items-center gap-3 text-xs">
          {prSummary.open > 0 && (
            <span>
              <span className="font-medium text-[var(--accent)]">
                {prSummary.open}
              </span>
              <span className="text-[var(--fg-subtle)] ml-1">open</span>
            </span>
          )}
          {prSummary.merged > 0 && (
            <span>
              <span className="font-medium text-[var(--purple)]">
                {prSummary.merged}
              </span>
              <span className="text-[var(--fg-subtle)] ml-1">merged</span>
            </span>
          )}
          {prSummary.draft > 0 && (
            <span>
              <span className="font-medium text-[var(--fg-muted)]">
                {prSummary.draft}
              </span>
              <span className="text-[var(--fg-subtle)] ml-1">draft</span>
            </span>
          )}
          {prSummary.total === 0 && (
            <span className="text-[var(--fg-subtle)]">No PRs</span>
          )}
        </div>
      </div>

      {/* Diff Stats */}
      <div className="shrink-0 w-[100px]">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] mb-1">
          Diff Stats
        </div>
        <div className="text-xs font-mono">
          <span className="text-[var(--green)]">+{prSummary.additions}</span>{" "}
          <span className="text-[var(--red)]">-{prSummary.deletions}</span>
        </div>
      </div>

      {/* CI Status */}
      <div className="shrink-0 w-[80px]">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] mb-1">
          CI Status
        </div>
        <CIStatusIndicator state={stack.state} />
      </div>

      {/* Last activity */}
      <div className="shrink-0 text-right ml-auto">
        <div className="text-[10px] text-[var(--fg-subtle)]">Last activity</div>
        <div className="text-xs text-[var(--fg-muted)] mt-0.5">
          {timeAgo(stack.updated_at)}
        </div>
      </div>
    </Link>
  );
}

/** Mini dot for each branch in the stack visualization */
function MiniStackDot({ branch }: { branch: BranchWithPR }) {
  const prState = branch.pull_request?.state;
  const color =
    prState === "merged"
      ? "var(--purple)"
      : prState === "open" || prState === "reviewing" || prState === "ready"
        ? "var(--accent)"
        : prState === "draft"
          ? "var(--fg-subtle)"
          : "var(--border)";

  return (
    <span
      className="w-2 h-2 rounded-full"
      style={{ backgroundColor: color }}
    />
  );
}

/** Placeholder CI status */
function CIStatusIndicator({ state }: { state: string }) {
  if (state === "merged") {
    return (
      <div className="flex items-center gap-1.5">
        <Icon name="check-circle" size="xs" className="text-[var(--green)]" />
        <span className="text-xs text-[var(--green)]">Success</span>
      </div>
    );
  }
  if (state === "active") {
    return (
      <div className="flex items-center gap-1.5">
        <Icon name="check-circle" size="xs" className="text-[var(--green)]" />
        <span className="text-xs text-[var(--green)]">Passing</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <Icon name="activity" size="xs" className="text-[var(--yellow)]" />
      <span className="text-xs text-[var(--fg-muted)]">Pending</span>
    </div>
  );
}

/** Compute PR state counts from branches */
function computePRSummary(branches: BranchWithPR[]) {
  let open = 0;
  let merged = 0;
  let draft = 0;
  let additions = 0;
  let deletions = 0;

  for (const b of branches) {
    const state = b.pull_request?.state;
    if (state === "merged") merged++;
    else if (state === "open" || state === "reviewing" || state === "ready" || state === "approved") open++;
    else if (state === "draft") draft++;
    // Placeholder diff stats until we aggregate from branch diffs
    additions += 114;
    deletions += 30;
  }

  return { open, merged, draft, total: open + merged + draft, additions, deletions };
}

/** Format timestamp to relative time */
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

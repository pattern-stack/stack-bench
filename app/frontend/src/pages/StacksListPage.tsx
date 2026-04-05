import { Link } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useProjectList } from "@/hooks/useProjectList";
import { useStackList } from "@/hooks/useStackList";
import type { Stack } from "@/types/stack";

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
      <h1 className="text-lg font-semibold text-[var(--fg-default)] mb-4">
        Stacks
      </h1>

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
        <div className="space-y-2">
          {stacks.map((stack) => (
            <StackRow key={stack.id} stack={stack} />
          ))}
        </div>
      )}
    </div>
  );
}

function StackRow({ stack }: { stack: Stack }) {
  const stateColors: Record<string, string> = {
    active: "var(--green)",
    submitted: "var(--accent)",
    draft: "var(--fg-subtle)",
    merged: "var(--purple)",
  };
  const dotColor = stateColors[stack.state] ?? "var(--fg-subtle)";

  return (
    <Link
      to={`/stacks/${stack.id}`}
      className="flex items-center gap-4 px-4 py-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] hover:border-[var(--border)] transition-colors"
    >
      {/* Icon + Name */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <Icon
          name="git-branch"
          size="sm"
          className="text-[var(--fg-muted)] shrink-0"
        />
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--fg-default)] truncate">
            {stack.name}
          </div>
          <div className="text-[10px] text-[var(--fg-subtle)] mt-0.5">
            trunk: {stack.trunk}
          </div>
        </div>
      </div>

      {/* State badge */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
        <span className="text-xs text-[var(--fg-muted)] capitalize">
          {stack.state}
        </span>
      </div>

      {/* Chevron */}
      <Icon
        name="chevron-right"
        size="sm"
        className="text-[var(--fg-subtle)] shrink-0"
      />
    </Link>
  );
}

StacksListPage.displayName = "StacksListPage";

export { StacksListPage };

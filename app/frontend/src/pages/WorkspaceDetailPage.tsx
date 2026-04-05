import { useParams } from "react-router-dom";
import { useTaskDetail } from "@/hooks/useTaskDetail";
import { Icon } from "@/components/atoms";
import type { AgentPhase } from "@/types/task";

function WorkspaceDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data, loading, error } = useTaskDetail(taskId);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--fg-muted)]">Loading workspace...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--red)]">
          {error ?? "Task not found"}
        </p>
      </div>
    );
  }

  const { task, job, agent_runs } = data;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Task header */}
      <div className="px-4 py-3 border-b border-[var(--border-muted)] flex items-center gap-3">
        <span className="text-xs font-mono text-[var(--fg-muted)]">
          {task.reference_number ?? task.id.slice(0, 8)}
        </span>
        <h1 className="text-sm font-semibold text-[var(--fg-default)] truncate">
          {task.title}
        </h1>
        <StatusBadge state={task.state} />
        {job && (
          <span className="text-xs text-[var(--fg-subtle)] ml-auto">
            {job.current_phase ?? job.state}
          </span>
        )}
      </div>

      {/* Pipeline bar */}
      {agent_runs.length > 0 && <PipelineBar phases={agent_runs} />}

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Chat area */}
        <div className="flex-[3] flex flex-col min-w-0 border-r border-[var(--border-muted)]">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {agent_runs.length === 0 ? (
              <div className="flex-1 flex items-center justify-center h-full">
                <div className="text-center">
                  <Icon name="message-square" size="lg" className="text-[var(--fg-subtle)] mx-auto mb-2" />
                  <p className="text-sm text-[var(--fg-muted)]">No agent activity yet</p>
                  <p className="text-xs text-[var(--fg-subtle)] mt-1">
                    Start a job to see agent chat here
                  </p>
                </div>
              </div>
            ) : (
              agent_runs.map((phase, i) => (
                <PhaseSection key={phase.id} phase={phase} index={i} />
              ))
            )}
          </div>

          {/* Chat input */}
          <div className="px-4 py-3 border-t border-[var(--border-muted)]">
            <div className="flex items-center gap-2 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-muted)] px-3 py-2">
              <input
                type="text"
                placeholder="Ask the agent..."
                className="flex-1 bg-transparent text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] outline-none"
              />
              <button className="text-[var(--accent)] hover:text-[var(--fg-default)] transition-colors">
                <Icon name="send" size="sm" />
              </button>
            </div>
          </div>
        </div>

        {/* Changes panel */}
        <div className="flex-[2] flex flex-col min-w-0">
          <div className="px-4 py-2 border-b border-[var(--border-muted)]">
            <div className="flex items-center gap-4">
              <span className="text-xs font-semibold text-[var(--fg-default)]">
                Changes
              </span>
              <span className="text-xs text-[var(--fg-subtle)]">
                History
              </span>
              <span className="text-xs text-[var(--fg-subtle)]">
                Discussion
              </span>
            </div>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <p className="text-xs text-[var(--fg-subtle)]">
              No changes yet
            </p>
          </div>

          {/* Bottom action bar */}
          <div className="px-4 py-3 border-t border-[var(--border-muted)] flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
              <Icon name="git-branch" size="xs" />
              <span className="font-mono">
                {job?.repo_branch ?? "no branch"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 text-xs text-[var(--fg-muted)] border border-[var(--border-muted)] rounded-md hover:border-[var(--border)] transition-colors">
                Add to Stack
              </button>
              <button className="px-3 py-1.5 text-xs text-[var(--fg-on-accent)] bg-[var(--accent)] rounded-md hover:opacity-90 transition-opacity">
                Create PR
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Compact pipeline bar */
function PipelineBar({ phases }: { phases: AgentPhase[] }) {
  return (
    <div className="px-4 py-2 border-b border-[var(--border-muted)] bg-[var(--bg-surface)]">
      <div className="flex items-center gap-1">
        {phases.map((phase, i) => (
          <div key={phase.id} className="flex items-center gap-1">
            {i > 0 && (
              <div className="w-4 h-px bg-[var(--border-muted)]" />
            )}
            <PhaseNode phase={phase} />
          </div>
        ))}
      </div>
    </div>
  );
}

function PhaseNode({ phase }: { phase: AgentPhase }) {
  const isActive = phase.state === "running";
  const isComplete = phase.state === "complete";
  const isFailed = phase.state === "failed";

  const dotColor = isActive
    ? "var(--green)"
    : isComplete
      ? "var(--fg-subtle)"
      : isFailed
        ? "var(--red)"
        : "var(--border-muted)";

  const duration =
    phase.duration_ms != null
      ? phase.duration_ms < 1000
        ? `${phase.duration_ms}ms`
        : `${Math.round(phase.duration_ms / 1000)}s`
      : null;

  return (
    <button className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-[var(--bg-canvas-inset)] transition-colors">
      {isComplete ? (
        <Icon name="check" size="xs" className="text-[var(--fg-subtle)]" />
      ) : (
        <span
          className={`w-2 h-2 rounded-full ${isActive ? "animate-pulse" : ""}`}
          style={{ backgroundColor: dotColor }}
        />
      )}
      <span
        className={`text-xs capitalize ${
          isActive
            ? "text-[var(--fg-default)] font-medium"
            : "text-[var(--fg-muted)]"
        }`}
      >
        {phase.phase}
      </span>
      {duration && (
        <span className="text-[10px] text-[var(--fg-subtle)]">{duration}</span>
      )}
    </button>
  );
}

function PhaseSection({
  phase,
}: {
  phase: AgentPhase;
  index: number;
}) {
  const roleColors: Record<string, string> = {
    architect: "var(--accent)",
    builder: "var(--green)",
    validator: "var(--purple)",
  };

  const color = roleColors[phase.phase] ?? "var(--fg-muted)";

  return (
    <div>
      {/* Phase divider */}
      <div className="flex items-center gap-3 my-4">
        <div className="flex-1 h-px bg-[var(--border-muted)]" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
          Phase: {phase.phase}
        </span>
        <div className="flex-1 h-px bg-[var(--border-muted)]" />
      </div>

      {/* Placeholder for actual messages */}
      <div className="flex items-start gap-3">
        <span
          className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-[var(--bg-canvas)] shrink-0"
          style={{ backgroundColor: color }}
        >
          {phase.phase.charAt(0).toUpperCase()}
        </span>
        <div className="text-sm text-[var(--fg-muted)]">
          {phase.state === "running"
            ? `${phase.phase} is working...`
            : phase.state === "complete"
              ? `${phase.phase} completed`
              : phase.state === "failed"
                ? `${phase.phase} failed`
                : `${phase.phase} pending`}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ state }: { state: string }) {
  const colors: Record<string, string> = {
    backlog: "var(--fg-subtle)",
    ready: "var(--yellow)",
    in_progress: "var(--accent)",
    in_review: "var(--purple)",
    done: "var(--green)",
    cancelled: "var(--red)",
  };
  const color = colors[state] ?? "var(--fg-subtle)";

  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-medium capitalize"
      style={{ color, border: `1px solid ${color}40` }}
    >
      {state.replace("_", " ")}
    </span>
  );
}

WorkspaceDetailPage.displayName = "WorkspaceDetailPage";

export { WorkspaceDetailPage };

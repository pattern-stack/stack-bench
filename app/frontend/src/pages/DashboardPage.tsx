import { Link } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useActiveProject } from "@/contexts/ProjectContext";
import { useTaskList } from "@/hooks/useTaskList";
import type { Task } from "@/types/task";

/** Active columns only — backlog removed per design direction */
const COLUMNS = [
  { key: "in_progress", label: "In Progress", states: ["in_progress"] },
  { key: "in_review", label: "Review", states: ["in_review"] },
  { key: "done", label: "Done", states: ["done"] },
] as const;

/** Shorten "TSK-2026-000042" → "TSK-042" */
function shortRef(ref: string | null, fallbackId: string): string {
  if (ref) {
    const lastSegment = ref.split("-").pop() ?? "";
    const num = parseInt(lastSegment, 10);
    if (!isNaN(num)) return `TSK-${String(num).padStart(3, "0")}`;
    return ref;
  }
  return fallbackId.slice(0, 6);
}

/** Demo pipeline data — will come from task detail API when wired */
const DEMO_PIPELINES: Record<string, PipelineStep[]> = {};

interface PipelineStep {
  role: string;
  state: "completed" | "active" | "pending";
  label?: string; // live status for active step
}

function demoPipeline(task: Task): PipelineStep[] {
  if (DEMO_PIPELINES[task.id]) return DEMO_PIPELINES[task.id];

  if (task.state === "in_progress") {
    return [
      { role: "Architect", state: "completed" },
      { role: "Builder", state: "active", label: "Editing src/auth/token.go..." },
      { role: "Validator", state: "pending" },
    ];
  }
  if (task.state === "in_review") {
    return [
      { role: "Architect", state: "completed" },
      { role: "Builder", state: "completed" },
      { role: "Validator", state: "active", label: "Running test suite..." },
    ];
  }
  if (task.state === "done") {
    return [
      { role: "Architect", state: "completed" },
      { role: "Builder", state: "completed" },
      { role: "Validator", state: "completed" },
    ];
  }
  return [];
}

function DashboardPage() {
  const { activeProject } = useActiveProject();
  const projectId = activeProject?.id;
  const { data: tasks, loading } = useTaskList(projectId);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--fg-muted)]">Loading tasks...</p>
      </div>
    );
  }

  // Separate backlog for a compact list below the kanban
  const backlogTasks = tasks.filter(
    (t) => t.state === "backlog" || t.state === "ready"
  );

  return (
    <div className="flex-1 flex flex-col min-h-0 p-6">
      <h1 className="text-lg font-semibold text-[var(--fg-default)] mb-4">
        Dashboard
      </h1>

      {/* Active kanban columns */}
      <div className="flex-1 flex gap-4 min-h-0 overflow-x-auto">
        {COLUMNS.map((col) => {
          const columnTasks = tasks.filter((t) =>
            (col.states as readonly string[]).includes(t.state)
          );
          return (
            <KanbanColumn
              key={col.key}
              label={col.label}
              tasks={columnTasks}
            />
          );
        })}
      </div>

      {/* Backlog as compact bottom strip */}
      {backlogTasks.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[var(--border-muted)]">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)]">
              Backlog
            </span>
            <span className="text-[10px] text-[var(--fg-subtle)] bg-[var(--bg-surface)] rounded-full px-1.5 py-0.5">
              {backlogTasks.length}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {backlogTasks.map((task) => (
              <Link
                key={task.id}
                to={`/workspaces/${task.id}`}
                className="px-3 py-1.5 rounded-md bg-[var(--bg-surface)] border border-[var(--border-muted)] hover:border-[var(--border)] transition-colors text-xs text-[var(--fg-muted)]"
              >
                <span className="font-mono text-[var(--fg-subtle)] mr-2">
                  {shortRef(task.reference_number, task.id)}
                </span>
                {task.title}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KanbanColumn({
  label,
  tasks,
}: {
  label: string;
  tasks: Task[];
}) {
  return (
    <div className="flex-1 min-w-[260px] flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--fg-muted)]">
          {label}
        </span>
        <span className="text-[10px] font-medium text-[var(--fg-subtle)] bg-[var(--bg-surface)] rounded-full px-1.5 py-0.5">
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 space-y-3.5 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="text-xs text-[var(--fg-subtle)] py-8 text-center">
            No tasks
          </div>
        ) : (
          tasks.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}

/** Role colors for pipeline nodes */
const ROLE_COLORS: Record<string, string> = {
  Architect: "var(--accent)",
  Builder: "var(--green)",
  Validator: "var(--purple)",
};

function TaskCard({ task }: { task: Task }) {
  const stateColor =
    task.state === "in_progress"
      ? "var(--accent)"
      : task.state === "in_review"
        ? "var(--purple)"
        : "transparent";

  const isDone = task.state === "done";
  const isActive = task.state === "in_progress" || task.state === "in_review";
  const taskId = shortRef(task.reference_number, task.id);
  const pipeline = demoPipeline(task);
  const activeStep = pipeline.find((s) => s.state === "active");

  return (
    <Link
      to={`/workspaces/${task.id}`}
      className={`block rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] px-4 py-3.5 hover:border-[var(--border)] transition-colors ${
        isDone ? "opacity-60" : ""
      }`}
      style={{
        borderLeftColor: stateColor,
        borderLeftWidth: stateColor !== "transparent" ? 3 : undefined,
      }}
    >
      {/* Row 1: Task ID + Priority */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono text-[var(--fg-subtle)]">
          {taskId}
        </span>
        <span className="px-1.5 py-0.5 rounded bg-[var(--bg-canvas)] text-[9px] text-[var(--fg-muted)] capitalize">
          {task.priority !== "none" ? task.priority : task.issue_type}
        </span>
      </div>

      {/* Row 2: Title (full, up to 2 lines) */}
      <div
        className={`text-sm font-medium leading-snug line-clamp-2 mb-3 ${
          isDone
            ? "line-through text-[var(--fg-muted)]"
            : "text-[var(--fg-default)]"
        }`}
      >
        {task.title}
      </div>

      {/* Row 3: Mini pipeline bar */}
      {pipeline.length > 0 && (
        <div className="flex items-center gap-1 mb-2">
          {pipeline.map((step, i) => (
            <div key={i} className="flex items-center gap-1">
              {i > 0 && (
                <div
                  className="w-3 h-px"
                  style={{
                    backgroundColor:
                      step.state === "pending"
                        ? "var(--border-muted)"
                        : "var(--border)",
                  }}
                />
              )}
              <PipelineNode step={step} />
            </div>
          ))}
        </div>
      )}

      {/* Row 4: Live agent status */}
      {activeStep && (
        <div className="flex items-center gap-1.5 mb-2">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse shrink-0" style={{ backgroundColor: ROLE_COLORS[activeStep.role] ?? "var(--green)" }} />
          <span className="text-[10px] text-[var(--fg-muted)] truncate">
            {activeStep.label ?? `${activeStep.role.toLowerCase()} working...`}
          </span>
        </div>
      )}

      {/* Row 5: Diff stats + PR */}
      {isActive && (
        <div className="flex items-center justify-between text-[10px]">
          <span>
            <span className="text-[var(--green)]">+142</span>{" "}
            <span className="text-[var(--red)]">-38</span>
          </span>
          <span className="font-mono text-[var(--accent)]">#190</span>
        </div>
      )}
    </Link>
  );
}

/** Single pipeline node inside a task card */
function PipelineNode({ step }: { step: PipelineStep }) {
  const color = ROLE_COLORS[step.role] ?? "var(--fg-muted)";

  if (step.state === "completed") {
    return (
      <div className="flex items-center gap-1">
        <Icon name="check" size="xs" className="text-[var(--fg-subtle)]" />
        <span className="text-[9px] text-[var(--fg-subtle)]">{step.role}</span>
      </div>
    );
  }

  if (step.state === "active") {
    return (
      <div className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full animate-pulse"
          style={{ backgroundColor: color }}
        />
        <span className="text-[9px] font-medium" style={{ color }}>
          {step.role}
        </span>
      </div>
    );
  }

  // pending
  return (
    <div className="flex items-center gap-1">
      <span className="w-2 h-2 rounded-full border border-[var(--border-muted)]" />
      <span className="text-[9px] text-[var(--fg-subtle)]">{step.role}</span>
    </div>
  );
}

DashboardPage.displayName = "DashboardPage";

export { DashboardPage };

import { Link } from "react-router-dom";
import { useProjectList } from "@/hooks/useProjectList";
import { useTaskList } from "@/hooks/useTaskList";
import type { Task } from "@/types/task";

/** Kanban column definition */
const COLUMNS = [
  { key: "backlog", label: "Backlog", states: ["backlog", "ready"] },
  { key: "in_progress", label: "In Progress", states: ["in_progress"] },
  { key: "in_review", label: "Review", states: ["in_review"] },
  { key: "done", label: "Done", states: ["done"] },
] as const;

function DashboardPage() {
  const { data: projects } = useProjectList();
  const projectId = projects[0]?.id;
  const { data: tasks, loading } = useTaskList(projectId);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--fg-muted)]">Loading tasks...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 p-6">
      <h1 className="text-lg font-semibold text-[var(--fg-default)] mb-4">
        Dashboard
      </h1>
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
    <div className="flex-1 min-w-[220px] flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--fg-muted)]">
          {label}
        </span>
        <span className="text-[10px] font-medium text-[var(--fg-subtle)] bg-[var(--bg-surface)] rounded-full px-1.5 py-0.5">
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="text-xs text-[var(--fg-subtle)] py-4 text-center">
            No tasks
          </div>
        ) : (
          tasks.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const stateColor =
    task.state === "in_progress"
      ? "var(--accent)"
      : task.state === "in_review"
        ? "var(--purple)"
        : "transparent";

  const isDone = task.state === "done";

  return (
    <Link
      to={`/workspaces/${task.id}`}
      className={`block rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] px-3 py-2.5 hover:border-[var(--border)] transition-colors ${
        isDone ? "opacity-60" : ""
      }`}
      style={{
        borderLeftColor: stateColor,
        borderLeftWidth: stateColor !== "transparent" ? 2 : undefined,
      }}
    >
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-mono text-[var(--fg-subtle)]">
          {task.reference_number ?? task.id.slice(0, 8)}
        </span>
        <span className={`text-sm text-[var(--fg-default)] leading-snug truncate ${isDone ? "line-through" : ""}`}>
          {task.title}
        </span>
      </div>
      <div className="mt-1.5 flex items-center gap-2 text-[10px] text-[var(--fg-subtle)]">
        <span className="px-1.5 py-0.5 rounded bg-[var(--bg-canvas)] capitalize">
          {task.priority !== "none" ? task.priority : task.issue_type}
        </span>
      </div>
    </Link>
  );
}

DashboardPage.displayName = "DashboardPage";

export { DashboardPage };

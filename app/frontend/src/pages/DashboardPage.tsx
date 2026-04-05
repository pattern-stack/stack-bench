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

/** Shorten "TSK-2026-000042" → "TSK-042" */
function shortRef(ref: string | null, fallbackId: string): string {
  if (ref) {
    // Extract the trailing number segment after the last hyphen
    const lastSegment = ref.split("-").pop() ?? "";
    const num = parseInt(lastSegment, 10);
    if (!isNaN(num)) return `TSK-${String(num).padStart(3, "0")}`;
    return ref;
  }
  return fallbackId.slice(0, 6);
}

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
  const isActive = task.state === "in_progress" || task.state === "in_review";
  const taskId = shortRef(task.reference_number, task.id);

  return (
    <Link
      to={`/workspaces/${task.id}`}
      className={`block rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] px-3 py-2 hover:border-[var(--border)] transition-colors ${
        isDone ? "opacity-50" : ""
      }`}
      style={{
        borderLeftColor: stateColor,
        borderLeftWidth: stateColor !== "transparent" ? 3 : undefined,
      }}
    >
      {/* Row 1: Task ID + Title */}
      <div className="flex gap-2 items-start">
        <span className="text-[9px] font-mono text-[var(--fg-subtle)] shrink-0 mt-0.5">
          {taskId}
        </span>
        <span
          className={`text-xs font-medium text-[var(--fg-default)] leading-snug line-clamp-2 ${
            isDone ? "line-through text-[var(--fg-muted)]" : ""
          }`}
        >
          {task.title}
        </span>
      </div>

      {/* Row 2: Agent status */}
      {isActive && (
        <div className="flex items-center gap-1.5 mt-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-pulse" />
          <span className="text-[9px] text-[var(--fg-muted)]">
            claude working...
          </span>
        </div>
      )}

      {/* Row 3: Priority + metadata */}
      <div className="flex items-center gap-1.5 mt-1.5">
        <span className="px-1.5 py-0.5 rounded bg-[var(--bg-canvas)] text-[9px] text-[var(--fg-muted)] capitalize">
          {task.priority !== "none" ? task.priority : task.issue_type}
        </span>
        {/* Placeholder diff stats — will be real when Task↔Stack linked */}
        {isActive && (
          <span className="text-[9px] ml-auto">
            <span className="text-[var(--green)]">+42</span>{" "}
            <span className="text-[var(--red)]">-8</span>
          </span>
        )}
      </div>
    </Link>
  );
}

DashboardPage.displayName = "DashboardPage";

export { DashboardPage };

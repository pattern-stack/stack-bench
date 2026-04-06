import { useLocation, useNavigate } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useProjectList } from "@/hooks/useProjectList";
import { useTaskList } from "@/hooks/useTaskList";
import { useStackList } from "@/hooks/useStackList";
import type { Task } from "@/types/task";
import type { Stack } from "@/types/stack";

type NavItem = "dashboard" | "workspaces" | "stacks";

function navFromPath(path: string): NavItem {
  if (path.startsWith("/workspaces")) return "workspaces";
  if (path.startsWith("/stacks")) return "stacks";
  return "dashboard";
}

/** Compact workspace card for sidebar task switching */
function WorkspaceCard({
  task,
  active,
  onClick,
}: {
  task: Task;
  active: boolean;
  onClick: () => void;
}) {
  const stateColor =
    task.state === "in_progress"
      ? "var(--accent)"
      : task.state === "in_review"
        ? "var(--purple)"
        : "var(--fg-subtle)";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
        active
          ? "bg-[var(--bg-canvas)] border-l-2 border-[var(--accent)]"
          : "hover:bg-[var(--bg-canvas-inset)]"
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ backgroundColor: stateColor }}
        />
        <span className="text-xs font-mono text-[var(--fg-muted)] shrink-0">
          {task.reference_number ?? task.id.slice(0, 8)}
        </span>
        <span className="text-sm text-[var(--fg-default)] truncate">
          {task.title}
        </span>
      </div>
      <div className="ml-4 mt-0.5 text-[10px] text-[var(--fg-subtle)]">
        {task.state.replace("_", " ")}
      </div>
    </button>
  );
}

/** Stack row for sidebar */
function StackRow({
  stack,
  onClick,
}: {
  stack: Stack;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-1.5 rounded-md hover:bg-[var(--bg-canvas-inset)] transition-colors"
    >
      <div className="flex items-center gap-2 min-w-0">
        <Icon name="git-branch" size="xs" className="text-[var(--fg-subtle)] shrink-0" />
        <span className="text-sm text-[var(--fg-default)] truncate">
          {stack.name}
        </span>
      </div>
    </button>
  );
}

function GlobalSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeNav = navFromPath(location.pathname);

  // Load project context
  const { data: projects } = useProjectList();
  const projectId = projects[0]?.id;

  // Load tasks & stacks for sidebar
  const { data: tasks } = useTaskList(projectId);
  const { data: stacks } = useStackList(projectId);

  // Active tasks for workspace section
  const activeTasks = tasks.filter(
    (t) => t.state === "in_progress" || t.state === "in_review" || t.state === "ready"
  );

  // Current workspace ID from URL
  const workspaceMatch = location.pathname.match(/^\/workspaces\/(.+)/);
  const activeTaskId = workspaceMatch?.[1] ?? null;

  return (
    <aside className="flex flex-col h-full w-[260px] border-r border-[var(--border)] bg-[var(--bg-surface)]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--border-muted)]">
        <div className="flex items-center gap-2">
          <Icon name="git-branch" size="sm" className="text-[var(--accent)]" />
          <span className="text-sm font-semibold text-[var(--fg-default)] tracking-tight">
            Stack Bench
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="px-2 py-2 space-y-0.5">
        <NavButton
          label="Dashboard"
          icon="grid"
          active={activeNav === "dashboard"}
          onClick={() => navigate("/")}
        />
        <NavButton
          label="Workspaces"
          icon="layout"
          active={activeNav === "workspaces"}
          onClick={() => navigate("/workspaces")}
        />
        <NavButton
          label="Stacks"
          icon="git-branch"
          active={activeNav === "stacks"}
          onClick={() => navigate("/stacks")}
        />
      </nav>

      {/* Workspaces section */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTasks.length > 0 && (
          <div className="px-2 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] px-3">
              Active Tasks
            </span>
            <div className="mt-1.5 space-y-0.5">
              {activeTasks.map((task) => (
                <WorkspaceCard
                  key={task.id}
                  task={task}
                  active={activeTaskId === task.id}
                  onClick={() => navigate(`/workspaces/${task.id}`)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Stacks section */}
        {stacks && stacks.length > 0 && (
          <div className="px-2 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--fg-subtle)] px-3">
              Stacks
            </span>
            <div className="mt-1.5 space-y-0.5">
              {stacks.map((stack) => (
                <StackRow
                  key={stack.id}
                  stack={stack}
                  onClick={() => navigate(`/stacks/${stack.id}`)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom actions */}
      <div className="px-3 py-3 border-t border-[var(--border-muted)] space-y-2">
        <button
          onClick={() => navigate("/?new=1")}
          className="w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-[var(--accent)] hover:bg-[var(--bg-canvas-inset)] transition-colors"
        >
          <Icon name="plus" size="xs" />
          New Task
        </button>
      </div>
    </aside>
  );
}

/** Sidebar nav button */
function NavButton({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
        active
          ? "bg-[var(--bg-canvas)] text-[var(--fg-default)] font-medium"
          : "text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--bg-canvas-inset)]"
      }`}
    >
      <Icon name={icon as any} size="sm" className={active ? "text-[var(--accent)]" : ""} />
      {label}
    </button>
  );
}

GlobalSidebar.displayName = "GlobalSidebar";

export { GlobalSidebar };

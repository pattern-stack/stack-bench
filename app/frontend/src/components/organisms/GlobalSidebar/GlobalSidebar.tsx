import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Icon } from "@/components/atoms";
import { useActiveProject } from "@/contexts/ProjectContext";
import { useTaskList } from "@/hooks/useTaskList";
import { useStackList } from "@/hooks/useStackList";
import { ProjectSwitcher } from "./ProjectSwitcher";
import { AddProjectDialog } from "@/components/organisms/AddProjectDialog";
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
        <span className="text-sm text-[var(--fg-default)] line-clamp-2">
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

interface GlobalSidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

function GlobalSidebar({ collapsed = false, onToggleCollapse }: GlobalSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const activeNav = navFromPath(location.pathname);
  const [showAddProject, setShowAddProject] = useState(false);

  // Load project context
  const { activeProject } = useActiveProject();
  const projectId = activeProject?.id;

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

  // --- Collapsed view: icon-only rail ---
  if (collapsed) {
    return (
      <aside className="flex flex-col h-full w-12 border-r border-[var(--border)] bg-[var(--bg-surface)] shrink-0">
        {/* Expand button */}
        <button
          onClick={onToggleCollapse}
          className="px-3 py-3 hover:bg-[var(--bg-canvas-inset)] transition-colors border-b border-[var(--border-muted)]"
          title="Expand sidebar"
        >
          <Icon name="chevron-right" size="sm" className="text-[var(--fg-subtle)]" />
        </button>

        {/* Nav icons */}
        <nav className="py-2 space-y-1 flex flex-col items-center">
          <NavIconButton
            icon="grid"
            active={activeNav === "dashboard"}
            onClick={() => navigate("/")}
            title="Dashboard"
          />
          <NavIconButton
            icon="layout"
            active={activeNav === "workspaces"}
            onClick={() => navigate("/workspaces")}
            title="Workspaces"
          />
          <NavIconButton
            icon="git-branch"
            active={activeNav === "stacks"}
            onClick={() => navigate("/stacks")}
            title="Stacks"
          />
        </nav>

        <AddProjectDialog isOpen={showAddProject} onClose={() => setShowAddProject(false)} />
      </aside>
    );
  }

  // --- Expanded view ---
  return (
    <aside className="flex flex-col h-full w-[260px] border-r border-[var(--border)] bg-[var(--bg-surface)] shrink-0">
      {/* Project Switcher */}
      <ProjectSwitcher onAddProject={() => setShowAddProject(true)} />

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
      <div className="px-3 py-2 border-t border-[var(--border-muted)] flex items-center justify-between">
        <button
          onClick={() => navigate("/?new=1")}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-[var(--accent)] hover:bg-[var(--bg-canvas-inset)] transition-colors"
        >
          <Icon name="plus" size="xs" />
          New Task
        </button>
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md text-[var(--fg-subtle)] hover:text-[var(--fg-default)] hover:bg-[var(--bg-canvas-inset)] transition-colors"
          title="Collapse sidebar"
        >
          <Icon name="chevron-left" size="xs" />
        </button>
      </div>

      <AddProjectDialog isOpen={showAddProject} onClose={() => setShowAddProject(false)} />
    </aside>
  );
}

/** Sidebar nav button (expanded) */
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

/** Sidebar nav button (collapsed — icon only) */
function NavIconButton({
  icon,
  active,
  onClick,
  title,
}: {
  icon: string;
  active: boolean;
  onClick: () => void;
  title: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`p-2 rounded-md transition-colors ${
        active
          ? "bg-[var(--bg-canvas)] text-[var(--accent)]"
          : "text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--bg-canvas-inset)]"
      }`}
    >
      <Icon name={icon as any} size="sm" />
    </button>
  );
}

GlobalSidebar.displayName = "GlobalSidebar";

export { GlobalSidebar };

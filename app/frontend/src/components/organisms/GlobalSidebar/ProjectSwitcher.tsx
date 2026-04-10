import { useState, useRef, useEffect, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/atoms";
import { useActiveProject } from "@/contexts/ProjectContext";
import { apiClient } from "@/generated/api/client";

interface ProjectSwitcherProps {
  onAddProject: () => void;
}

function ProjectSwitcher({ onAddProject }: ProjectSwitcherProps) {
  const { activeProject, setActiveProject, projects } = useActiveProject();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  // Close on ESC
  useEffect(() => {
    if (!isOpen) return;

    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen]);

  const queryClient = useQueryClient();
  const syncMutation = useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<{ synced: unknown[]; skipped: string[] }>(
        `/api/v1/projects/${projectId}/sync-stacks`,
        {}
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stacks"] });
    },
  });

  const handleSync = useCallback(() => {
    if (activeProject?.id) {
      syncMutation.mutate(activeProject.id);
    }
  }, [activeProject?.id, syncMutation]);

  const displayName = activeProject?.name ?? "Add a project";

  return (
    <div ref={containerRef} className="relative border-b border-[var(--border-muted)]">
      <div className="flex items-center">
        <button
          onClick={() => (projects.length > 0 ? setIsOpen(!isOpen) : onAddProject())}
          className="flex-1 flex items-center gap-2 px-4 py-3 hover:bg-[var(--bg-canvas-inset)] transition-colors min-w-0"
        >
          <Icon name="folder" size="sm" className="text-[var(--accent)] shrink-0" />
          <span className="text-sm font-semibold text-[var(--fg-default)] tracking-tight truncate flex-1 text-left">
            {displayName}
          </span>
          {projects.length > 0 && (
            <Icon
              name="chevron-down"
              size="xs"
              className={`text-[var(--fg-subtle)] shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
            />
          )}
        </button>
        {activeProject && (
          <button
            onClick={handleSync}
            disabled={syncMutation.isPending}
            title="Sync stacks from CLI"
            className="px-2 py-3 text-[var(--fg-subtle)] hover:text-[var(--accent)] transition-colors disabled:opacity-50"
          >
            <Icon
              name="git-branch"
              size="xs"
              className={syncMutation.isPending ? "animate-spin" : ""}
            />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 z-50 mt-0.5 mx-2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] shadow-lg overflow-hidden">
          <div className="py-1 max-h-[240px] overflow-y-auto">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  setActiveProject(project);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                  project.id === activeProject?.id
                    ? "bg-[var(--bg-canvas)] text-[var(--fg-default)]"
                    : "text-[var(--fg-muted)] hover:bg-[var(--bg-canvas-inset)] hover:text-[var(--fg-default)]"
                }`}
              >
                <span className="flex-1 truncate">{project.name}</span>
                {project.id === activeProject?.id && (
                  <Icon name="check" size="xs" className="text-[var(--accent)] shrink-0" />
                )}
              </button>
            ))}
          </div>

          <div className="border-t border-[var(--border-muted)]">
            <button
              onClick={() => {
                setIsOpen(false);
                onAddProject();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--accent)] hover:bg-[var(--bg-canvas-inset)] transition-colors"
            >
              <Icon name="plus" size="xs" />
              Add Project
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

ProjectSwitcher.displayName = "ProjectSwitcher";

export { ProjectSwitcher };

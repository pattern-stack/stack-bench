import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { useProjectList } from "@/hooks/useProjectList";

const STORAGE_KEY = "stack-bench-active-project";

interface Project {
  id: string;
  name: string;
  github_repo: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

interface ProjectContextValue {
  activeProject: Project | null;
  setActiveProject: (project: Project | null) => void;
  projects: Project[];
  isLoading: boolean;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { data: projects, loading } = useProjectList();
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY)
  );

  // Resolve the active project from the list
  const activeProject =
    projects.find((p) => p.id === activeProjectId) ?? projects[0] ?? null;

  // Sync the resolved project ID back (handles case where saved ID is stale)
  useEffect(() => {
    if (!loading && projects.length > 0 && activeProject) {
      if (activeProject.id !== activeProjectId) {
        setActiveProjectId(activeProject.id);
        localStorage.setItem(STORAGE_KEY, activeProject.id);
      }
    }
  }, [loading, projects, activeProject, activeProjectId]);

  const setActiveProject = useCallback((project: Project | null) => {
    if (project) {
      setActiveProjectId(project.id);
      localStorage.setItem(STORAGE_KEY, project.id);
    } else {
      setActiveProjectId(null);
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        activeProject,
        setActiveProject,
        projects,
        isLoading: loading,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useActiveProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error(
      "useActiveProject must be used within a ProjectProvider"
    );
  }
  return ctx;
}

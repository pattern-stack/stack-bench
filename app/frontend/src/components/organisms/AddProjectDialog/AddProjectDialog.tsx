import { useState, useCallback, useEffect } from "react";
import { Dialog } from "@/components/atoms";
import { useActiveProject } from "@/contexts/ProjectContext";
import { useCreateLocalProject } from "@/hooks/useCreateLocalProject";

interface AddProjectDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function AddProjectDialog({ isOpen, onClose }: AddProjectDialogProps) {
  const { setActiveProject } = useActiveProject();
  const mutation = useCreateLocalProject();

  const [name, setName] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [description, setDescription] = useState("");
  const [nameManuallyEdited, setNameManuallyEdited] = useState(false);

  // Reset form on open
  useEffect(() => {
    if (isOpen) {
      setName("");
      setLocalPath("");
      setDescription("");
      setNameManuallyEdited(false);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Auto-derive name from folder name if user hasn't manually edited it
  const handleLocalPathChange = useCallback(
    (value: string) => {
      setLocalPath(value);
      if (!nameManuallyEdited) {
        const parts = value.replace(/\/+$/, "").split("/");
        const folderName = parts[parts.length - 1] ?? "";
        setName(folderName);
      }
    },
    [nameManuallyEdited]
  );

  const handleNameChange = useCallback((value: string) => {
    setName(value);
    setNameManuallyEdited(true);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!name.trim() || !localPath.trim()) return;

      try {
        const result = await mutation.mutateAsync({
          name: name.trim(),
          local_path: localPath.trim(),
          description: description.trim() || undefined,
        });

        // Set the new project as active
        setActiveProject({
          id: result.project_id,
          name: result.project_name,
          github_repo: "",
          owner_id: "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });

        onClose();
      } catch {
        // Error is handled by mutation.error below
      }
    },
    [name, localPath, description, mutation, setActiveProject, onClose]
  );

  // Extract error message from mutation error
  const errorMessage = mutation.error
    ? (mutation.error as { detail?: string }).detail ??
      (mutation.error as Error).message ??
      "Failed to create project"
    : null;

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Add Project">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Local Path */}
        <div>
          <label
            htmlFor="add-project-path"
            className="block text-xs font-medium text-[var(--fg-muted)] mb-1"
          >
            Local Path <span className="text-[var(--red)]">*</span>
          </label>
          <div className="flex gap-2">
            <input
              id="add-project-path"
              type="text"
              value={localPath}
              onChange={(e) => handleLocalPathChange(e.target.value)}
              placeholder="/Users/you/Projects/my-repo"
              required
              className="flex-1 px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--bg-canvas)] text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] focus:outline-none focus:border-[var(--accent)] transition-colors"
            />
            {"showDirectoryPicker" in window && (
              <button
                type="button"
                onClick={async () => {
                  try {
                    const handle = await (window as any).showDirectoryPicker({ mode: "read" });
                    // Resolve the full path — unfortunately the File System Access API
                    // only gives us the folder name, not the full path. We set it as a
                    // hint and let the user confirm/edit.
                    handleLocalPathChange(handle.name);
                  } catch {
                    // User cancelled the picker
                  }
                }}
                className="px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--bg-canvas)] text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:border-[var(--accent)] transition-colors shrink-0"
                title="Browse for folder"
              >
                Browse
              </button>
            )}
          </div>
          <p className="mt-1 text-[10px] text-[var(--fg-subtle)]">
            Absolute path to a local git repository
          </p>
        </div>

        {/* Name */}
        <div>
          <label
            htmlFor="add-project-name"
            className="block text-xs font-medium text-[var(--fg-muted)] mb-1"
          >
            Name <span className="text-[var(--red)]">*</span>
          </label>
          <input
            id="add-project-name"
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="my-project"
            required
            className="w-full px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--bg-canvas)] text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] focus:outline-none focus:border-[var(--accent)] transition-colors"
          />
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="add-project-description"
            className="block text-xs font-medium text-[var(--fg-muted)] mb-1"
          >
            Description
          </label>
          <textarea
            id="add-project-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional project description"
            rows={2}
            className="w-full px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--bg-canvas)] text-sm text-[var(--fg-default)] placeholder:text-[var(--fg-subtle)] focus:outline-none focus:border-[var(--accent)] transition-colors resize-none"
          />
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="px-3 py-2 rounded-md bg-[var(--red)]/10 border border-[var(--red)]/20 text-xs text-[var(--red)]">
            {errorMessage}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)] hover:bg-[var(--bg-canvas-inset)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || !localPath.trim() || mutation.isPending}
            className="px-4 py-1.5 rounded-md text-sm font-medium bg-[var(--accent)] text-[var(--fg-on-accent)] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? "Creating..." : "Create Project"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

AddProjectDialog.displayName = "AddProjectDialog";

export { AddProjectDialog };
export type { AddProjectDialogProps };

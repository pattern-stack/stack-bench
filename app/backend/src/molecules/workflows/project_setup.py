import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from features.projects.schemas.input import ProjectCreate
from features.projects.service import ProjectService
from features.workspaces.schemas.input import WorkspaceCreate
from features.workspaces.service import WorkspaceService
from molecules.exceptions import MoleculeError


@dataclass
class ProjectSetupResult:
    project_id: UUID
    workspace_id: UUID
    project_name: str


class ProjectSetupError(MoleculeError):
    """Raised when project setup fails.

    Extends MoleculeError so the global molecule_exception_handler in app.py
    catches it automatically.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


async def _run_git(local_path: str, *args: str) -> tuple[bool, str]:
    """Run a git command in the given directory, return (success, stdout)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        local_path,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, _ = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8").strip()
    return proc.returncode == 0, stdout


def _detect_provider(remote_url: str) -> str:
    """Detect git provider from a remote URL."""
    if "github.com" in remote_url:
        return "github"
    if "gitlab.com" in remote_url:
        return "gitlab"
    if "bitbucket.org" in remote_url:
        return "bitbucket"
    return "local"


def _normalize_remote_url(remote_url: str) -> str:
    """Convert SSH remote URLs to HTTPS format for github_repo field."""
    # git@github.com:owner/repo.git -> https://github.com/owner/repo
    if remote_url.startswith("git@"):
        url = remote_url.replace(":", "/", 1).replace("git@", "https://")
        if url.endswith(".git"):
            url = url[:-4]
        return url
    # Already HTTPS — strip trailing .git
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]
    return remote_url


@dataclass
class ProjectSetupWorkflow:
    """Create a project + workspace from a local git repository path.

    This workflow is a molecule that composes ProjectService and WorkspaceService.
    It validates the local path, reads git metadata, and creates both entities
    in a single transaction.
    """

    db: AsyncSession
    project_service: ProjectService = field(default_factory=ProjectService)
    workspace_service: WorkspaceService = field(default_factory=WorkspaceService)

    async def create_local_project(
        self,
        user_id: UUID,
        name: str,
        local_path: str,
        description: str | None = None,
    ) -> ProjectSetupResult:
        """Create a project and workspace from a local git repository.

        Args:
            user_id: The authenticated user's ID.
            name: Project display name.
            local_path: Absolute path to a local git repository.
            description: Optional project description.
        """
        # 1. Validate local_path exists and is a git repo
        path = Path(local_path)
        if not path.exists():
            raise ProjectSetupError(f"Directory does not exist: {local_path}")
        if not path.is_dir():
            raise ProjectSetupError(f"Path is not a directory: {local_path}")
        if not (path / ".git").exists():
            raise ProjectSetupError(f"Not a git repository: {local_path}")

        # 2. Read git remote origin URL
        success, remote_url = await _run_git(local_path, "remote", "get-url", "origin")
        folder_name = path.name
        if success and remote_url:
            normalized_url = _normalize_remote_url(remote_url)
            provider = _detect_provider(remote_url)
            repo_url = normalized_url
            # github_repo field has a validator requiring "github.com" in the URL.
            # For non-GitHub remotes, use a synthetic GitHub URL as a placeholder.
            github_repo = normalized_url if provider == "github" else f"https://github.com/local/{folder_name}"
        else:
            # No remote — use synthetic URL
            github_repo = f"https://github.com/local/{folder_name}"
            repo_url = github_repo
            provider = "local"

        # 3. Read default branch
        success, branch = await _run_git(local_path, "symbolic-ref", "--short", "HEAD")
        default_branch = branch if success and branch else "main"

        # 4. Check for duplicate project name
        existing = await self.project_service.get_by_name(self.db, name)
        if existing:
            raise ProjectSetupError(f"Project '{name}' already exists")

        # 5. Create Project
        project = await self.project_service.create(
            self.db,
            ProjectCreate(
                name=name,
                description=description or f"Local repository: {path.name}",
                owner_id=user_id,
                github_repo=github_repo,
                local_path=local_path,
                metadata_={"source": "local_setup", "local_path": local_path},
            ),
        )

        # 6. Create Workspace
        workspace = await self.workspace_service.create(
            self.db,
            WorkspaceCreate(
                project_id=project.id,
                name=f"{name} (local)",
                repo_url=repo_url,
                provider=provider,
                default_branch=default_branch,
                local_path=local_path,
            ),
        )

        # 7. Transition project to active
        project.transition_to("active")

        await self.db.flush()

        return ProjectSetupResult(
            project_id=project.id,
            workspace_id=workspace.id,
            project_name=project.name,
        )

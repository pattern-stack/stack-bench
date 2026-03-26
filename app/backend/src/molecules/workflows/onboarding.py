from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from features.projects.schemas.input import ProjectCreate
from features.projects.service import ProjectService
from features.workspaces.schemas.input import WorkspaceCreate
from features.workspaces.service import WorkspaceService
from molecules.apis.github_oauth_api import GitHubOAuthAPI
from molecules.exceptions import MoleculeError

GITHUB_ORGS_URL = "https://api.github.com/user/orgs"
GITHUB_INSTALLATIONS_URL = "https://api.github.com/user/installations"
GITHUB_INSTALL_REPOS_URL = "https://api.github.com/user/installations/{installation_id}/repositories"
GITHUB_USER_REPOS_URL = "https://api.github.com/user/repos"
GITHUB_ORG_REPOS_URL = "https://api.github.com/orgs/{org}/repos"


@dataclass
class OnboardingStatus:
    needs_onboarding: bool
    has_github: bool
    has_project: bool


@dataclass
class GitHubOrg:
    login: str
    avatar_url: str
    description: str | None = None
    installed: bool = False
    installation_id: int | None = None
    account_type: str = "Organization"  # "User" or "Organization"


@dataclass
class GitHubRepo:
    full_name: str  # "owner/repo"
    name: str
    private: bool
    default_branch: str
    description: str | None = None
    html_url: str = ""


@dataclass
class OnboardingResult:
    project_id: UUID
    workspace_id: UUID
    project_name: str


@dataclass
class OnboardingWorkflow:
    """Multi-step onboarding: GitHub connect -> org/repo select -> project creation.

    This workflow is a molecule that composes ProjectService, WorkspaceService,
    and GitHubOAuthAPI. It contains the business logic for the onboarding flow.
    The organism router is a thin interface over this.
    """

    db: AsyncSession
    github_oauth: GitHubOAuthAPI = field(default_factory=GitHubOAuthAPI)
    project_service: ProjectService = field(default_factory=ProjectService)
    workspace_service: WorkspaceService = field(default_factory=WorkspaceService)

    async def get_status(self, user_id: UUID) -> OnboardingStatus:
        """Check onboarding status: does the user have GitHub connected?"""
        github_status = await self.github_oauth.get_connection_status(self.db, user_id)
        has_github = github_status["connected"]

        # Check if user has any GitHub App installations (app installed somewhere)
        has_installations = False
        if has_github:
            token = await self.github_oauth.get_user_github_token(self.db, user_id)
            if token:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        GITHUB_INSTALLATIONS_URL,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                        },
                    )
                    if resp.status_code == 200:
                        installations = resp.json().get("installations", [])
                        has_installations = len(installations) > 0

        return OnboardingStatus(
            needs_onboarding=not has_installations,
            has_github=has_github,
            has_project=has_installations,
        )

    async def mark_complete(self, user_id: UUID) -> None:
        """Mark onboarding as complete. No-op — status is derived from GitHub state."""
        # Onboarding completion is determined by having GitHub connected + app installed.
        # This endpoint exists so the frontend has a clear "done" action.
        pass

    async def list_github_orgs(self, user_id: UUID) -> list[GitHubOrg]:
        """List all accounts (personal + orgs) with their app installation status.

        Combines:
        - /user (personal account — always shown)
        - /user/orgs (orgs the user belongs to — requires read:org)
        - /user/installations (where the app is installed)

        Each entry indicates whether the app is installed, so the frontend
        can show "Install" vs "Select" for each account.
        """
        token = await self.github_oauth.get_user_github_token(self.db, user_id)
        if not token:
            raise OnboardingError("GitHub not connected")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            # Only source of truth: /user/installations
            # Shows accounts where the GitHub App is actually installed.
            inst_response = await client.get(GITHUB_INSTALLATIONS_URL, headers=headers, params={"per_page": 100})

        result: list[GitHubOrg] = []
        if inst_response.status_code == 200:
            for inst in inst_response.json().get("installations", []):
                account = inst.get("account", {})
                account_type = account.get("type", "User")
                result.append(
                    GitHubOrg(
                        login=account.get("login", ""),
                        avatar_url=account.get("avatar_url", ""),
                        description="Personal account" if account_type == "User" else "Organization",
                        installed=True,
                        installation_id=inst["id"],
                        account_type=account_type,
                    )
                )

        return result

    async def list_github_repos(self, user_id: UUID, org: str | None = None) -> list[GitHubRepo]:
        """List repos accessible via the GitHub App installation for a given account.

        Uses /user/installations to find the installation_id for the account,
        then /user/installations/{id}/repositories to list repos the app can access.
        """
        token = await self.github_oauth.get_user_github_token(self.db, user_id)
        if not token:
            raise OnboardingError("GitHub not connected")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            # Find the installation_id for this account
            inst_response = await client.get(
                GITHUB_INSTALLATIONS_URL,
                headers=headers,
                params={"per_page": 100},
            )
            inst_response.raise_for_status()
            installations = inst_response.json().get("installations", [])

            installation_id = None
            for inst in installations:
                if inst.get("account", {}).get("login") == org:
                    installation_id = inst["id"]
                    break

            if installation_id is None:
                # Fallback: use /user/repos filtered by owner
                response = await client.get(
                    GITHUB_USER_REPOS_URL,
                    headers=headers,
                    params={"per_page": 100, "sort": "pushed", "affiliation": "owner"},
                )
                response.raise_for_status()
                repos_data: list[dict[str, Any]] = response.json()
            else:
                # Use installation repos endpoint
                response = await client.get(
                    GITHUB_INSTALL_REPOS_URL.format(installation_id=installation_id),
                    headers=headers,
                    params={"per_page": 100},
                )
                response.raise_for_status()
                repos_data = response.json().get("repositories", [])

        return [
            GitHubRepo(
                full_name=r["full_name"],
                name=r["name"],
                private=r["private"],
                default_branch=r.get("default_branch", "main"),
                description=r.get("description"),
                html_url=r.get("html_url", ""),
            )
            for r in repos_data
        ]

    async def complete(
        self,
        user_id: UUID,
        repo_full_name: str,
        default_branch: str = "main",
    ) -> OnboardingResult:
        """Create Project + Workspace from the selected GitHub repo.

        Args:
            user_id: The authenticated user's ID.
            repo_full_name: "owner/repo" format.
            default_branch: The repo's default branch (from GitHub API).
        """
        repo_url = f"https://github.com/{repo_full_name}"

        # Use full_name (org/repo) as project name to avoid collisions
        project_name = repo_full_name

        # 1. Check for duplicate project
        existing = await self.project_service.get_by_name(self.db, project_name)
        if existing:
            raise OnboardingError(f"Project '{project_name}' already exists")

        # 2. Create Project in setup state
        project = await self.project_service.create(
            self.db,
            ProjectCreate(
                name=project_name,
                description=f"GitHub repository: {repo_full_name}",
                owner_id=user_id,
                github_repo=repo_url,
                metadata_={"github_full_name": repo_full_name},
            ),
        )

        # 3. Create Workspace
        workspace = await self.workspace_service.create(
            self.db,
            WorkspaceCreate(
                project_id=project.id,
                name=f"{project_name} (GitHub)",
                repo_url=repo_url,
                provider="github",
                default_branch=default_branch,
            ),
        )

        # 4. Transition project to active
        project.transition_to("active")

        await self.db.flush()

        return OnboardingResult(
            project_id=project.id,
            workspace_id=workspace.id,
            project_name=project.name,
        )


class OnboardingError(MoleculeError):
    """Raised when onboarding fails.

    Extends MoleculeError so the global molecule_exception_handler in app.py
    catches it automatically. The router try/except blocks are optional but
    allow for endpoint-specific HTTP status codes (e.g. 400 vs 500).
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

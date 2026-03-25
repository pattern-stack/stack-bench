---
title: "GitHub Onboarding Flow"
date: 2026-03-25
status: draft
branch: ""
depends_on: ["sb-117-github-oauth"]
adrs: []
---

# GitHub Onboarding Flow

## Goal

After a user registers or logs in, guide them through connecting their GitHub account and selecting an org + repo, then create a Project + Workspace so they land on a working stack view. The onboarding workflow lives in the backend molecules layer; the frontend is a thin multi-step UI that calls backend APIs and renders state.

## Flow Overview

```
Register / Login
       |
       v
  [Onboarding Check]  -- already has a Project? --> skip to App
       |
       no Project
       v
  Step 1: Connect GitHub (OAuth popup)
       |
       v
  Step 2: Select Org  (GET /onboarding/github/orgs)
       |
       v
  Step 3: Select Repo (GET /onboarding/github/repos?org=X)
       |
       v
  Step 4: Complete    (POST /onboarding/complete)
       |               - creates Project (state=setup)
       |               - creates Workspace
       |               - transitions Project to active
       |               - triggers initial sync job
       v
  Redirect to App (stack view)
```

## Architecture Decisions

### Layer Placement

| Component | Layer | Rationale |
|-----------|-------|-----------|
| `OnboardingWorkflow` | Molecule (workflow) | Multi-step process composing ProjectService, WorkspaceService, GitHubOAuthAPI, and GitHub API calls |
| `GET /onboarding/github/orgs` | Organism (router) | Thin endpoint delegating to workflow |
| `GET /onboarding/github/repos` | Organism (router) | Thin endpoint delegating to workflow |
| `POST /onboarding/complete` | Organism (router) | Thin endpoint delegating to workflow |
| `GET /onboarding/status` | Organism (router) | Returns onboarding state for current user |
| `OnboardingPage` | Frontend page | Multi-step wizard, no business logic |

### Pattern Choices

- **Project**: Already an `EventPattern` with `setup -> active -> archived` states. Onboarding creates it in `setup` and transitions to `active` on completion. No model changes needed beyond adding `owner_id`.
- **Workspace**: Already a `BasePattern`. Created as part of onboarding. No changes needed.
- **No new pattern-stack model**: Onboarding state is derived from whether the user has a Project, not stored as a separate entity. This avoids unnecessary state tracking.

### Key Design Decision: owner_id on Project

The Project model currently has no user association. We need to add `owner_id: UUID` (FK to `users.id`) so each project belongs to a user. This also enables the onboarding status check ("does this user have any projects?") and future multi-user scoping.

The `local_path` field on Project is currently `required=True` with a path-existence validator. For onboarding from GitHub (remote-first), we need to make `local_path` nullable/optional since the user is selecting a remote repo, not a local directory. This aligns with the remote-first architecture decision documented in memory.

## Data Model Changes

### Project Model (modify)

```python
# app/backend/src/features/projects/models.py

class Project(EventPattern):
    __tablename__ = "projects"

    class Pattern:
        entity = "project"
        reference_prefix = "PROJ"
        initial_state = "setup"
        states = {
            "setup": ["active"],
            "active": ["archived"],
            "archived": [],
        }
        state_phases = {
            "setup": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "archived": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    name = Field(str, required=True, max_length=200, unique=True, index=True)
    description = Field(str, nullable=True)
    metadata_ = Field(dict, default=dict)
    owner_id = Field(UUID, foreign_key="users.id", required=True, index=True)  # NEW
    local_path = Field(str, nullable=True, max_length=500)                      # CHANGED: was required
    github_repo = Field(str, required=True, max_length=500, index=True)
```

### ProjectCreate Schema (modify)

```python
# app/backend/src/features/projects/schemas/input.py

class ProjectCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None
    owner_id: UUID                                                    # NEW
    local_path: str | None = None                                     # CHANGED: was required
    github_repo: str = PydanticField(..., min_length=1, max_length=500)

    @field_validator("local_path")
    @classmethod
    def validate_local_path_exists(cls, v: str | None) -> str | None:
        """Validate that local_path points to an existing directory (skip if None)."""
        if v is None:
            return v
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v
```

### ProjectResponse Schema (modify)

```python
# app/backend/src/features/projects/schemas/output.py

class ProjectResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    description: str | None = None
    metadata_: dict[str, Any]
    state: str
    created_at: datetime
    updated_at: datetime
    owner_id: UUID                     # NEW
    local_path: str | None = None      # CHANGED: was required str
    github_repo: str

    model_config = {"from_attributes": True}
```

### ProjectService (modify)

```python
# app/backend/src/features/projects/service.py -- add method

async def get_by_owner(self, db: AsyncSession, owner_id: UUID) -> list[Project]:
    result = await db.execute(
        select(Project).where(
            Project.owner_id == owner_id,
            Project.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
```

### Migration

New alembic migration:
- Add `owner_id` column to `projects` (UUID, FK to `users.id`, NOT NULL)
- Alter `local_path` to nullable
- Add index on `projects.owner_id`

For existing projects (if any in dev), set `owner_id` to a default user or drop and recreate.

## Backend: Onboarding Workflow (Molecule)

### File: `app/backend/src/molecules/workflows/onboarding.py`

```python
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from features.projects.service import ProjectService
from features.projects.schemas.input import ProjectCreate
from features.workspaces.service import WorkspaceService
from features.workspaces.schemas.input import WorkspaceCreate
from molecules.apis.github_oauth_api import GitHubOAuthAPI
from molecules.exceptions import MoleculeError


GITHUB_ORGS_URL = "https://api.github.com/user/orgs"
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


@dataclass
class GitHubRepo:
    full_name: str        # "owner/repo"
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
        """Check onboarding status: does the user have GitHub + a Project?"""
        github_status = await self.github_oauth.get_connection_status(self.db, user_id)
        has_github = github_status["connected"]

        projects = await self.project_service.get_by_owner(self.db, user_id)
        has_project = len(projects) > 0

        return OnboardingStatus(
            needs_onboarding=not has_project,
            has_github=has_github,
            has_project=has_project,
        )

    async def list_github_orgs(self, user_id: UUID) -> list[GitHubOrg]:
        """List GitHub orgs the user belongs to, plus a personal account entry."""
        token = await self.github_oauth.get_user_github_token(self.db, user_id)
        if not token:
            raise OnboardingError("GitHub not connected")

        # Fetch user profile for personal account
        github_user = await self.github_oauth.get_github_user(token)
        personal = GitHubOrg(
            login=github_user["login"],
            avatar_url=github_user.get("avatar_url", ""),
            description="Personal account",
        )

        # Fetch orgs
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GITHUB_ORGS_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                params={"per_page": 100},
            )
            response.raise_for_status()
            orgs_data = response.json()

        orgs = [
            GitHubOrg(
                login=o["login"],
                avatar_url=o.get("avatar_url", ""),
                description=o.get("description"),
            )
            for o in orgs_data
        ]

        return [personal] + orgs

    async def list_github_repos(
        self, user_id: UUID, org: str | None = None
    ) -> list[GitHubRepo]:
        """List repos for an org, or the user's personal repos."""
        token = await self.github_oauth.get_user_github_token(self.db, user_id)
        if not token:
            raise OnboardingError("GitHub not connected")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            if org:
                # Check if org is the user's personal account
                github_user = await self.github_oauth.get_github_user(token)
                if org == github_user["login"]:
                    # Personal repos
                    response = await client.get(
                        GITHUB_USER_REPOS_URL,
                        headers=headers,
                        params={
                            "per_page": 100,
                            "sort": "pushed",
                            "affiliation": "owner",
                        },
                    )
                else:
                    # Org repos
                    response = await client.get(
                        GITHUB_ORG_REPOS_URL.format(org=org),
                        headers=headers,
                        params={"per_page": 100, "sort": "pushed"},
                    )
            else:
                # All repos the user can access
                response = await client.get(
                    GITHUB_USER_REPOS_URL,
                    headers=headers,
                    params={"per_page": 100, "sort": "pushed"},
                )

            response.raise_for_status()
            repos_data = response.json()

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
        # (e.g. two users both have a repo called "backend")
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
```

## Backend: Onboarding Router (Organism)

### File: `app/backend/src/organisms/api/routers/onboarding.py`

Thin interface that delegates everything to `OnboardingWorkflow`.

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from molecules.workflows.onboarding import OnboardingWorkflow, OnboardingError
from organisms.api.dependencies import CurrentUser, DatabaseSession

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# --- Response schemas ---

class OnboardingStatusResponse(BaseModel):
    needs_onboarding: bool
    has_github: bool
    has_project: bool


class GitHubOrgResponse(BaseModel):
    login: str
    avatar_url: str
    description: str | None = None


class GitHubRepoResponse(BaseModel):
    full_name: str
    name: str
    private: bool
    default_branch: str
    description: str | None = None


class OnboardingCompleteRequest(BaseModel):
    repo_full_name: str       # "owner/repo"
    default_branch: str = "main"


class OnboardingCompleteResponse(BaseModel):
    project_id: str
    workspace_id: str
    project_name: str


# --- Endpoints ---

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: CurrentUser, db: DatabaseSession
) -> OnboardingStatusResponse:
    workflow = OnboardingWorkflow(db)
    status = await workflow.get_status(user.id)
    return OnboardingStatusResponse(
        needs_onboarding=status.needs_onboarding,
        has_github=status.has_github,
        has_project=status.has_project,
    )


@router.get("/github/orgs", response_model=list[GitHubOrgResponse])
async def list_github_orgs(
    user: CurrentUser, db: DatabaseSession
) -> list[GitHubOrgResponse]:
    workflow = OnboardingWorkflow(db)
    try:
        orgs = await workflow.list_github_orgs(user.id)
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return [GitHubOrgResponse(**vars(o)) for o in orgs]


@router.get("/github/repos", response_model=list[GitHubRepoResponse])
async def list_github_repos(
    user: CurrentUser,
    db: DatabaseSession,
    org: str | None = None,
) -> list[GitHubRepoResponse]:
    workflow = OnboardingWorkflow(db)
    try:
        repos = await workflow.list_github_repos(user.id, org=org)
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return [GitHubRepoResponse(**vars(r)) for r in repos]


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    data: OnboardingCompleteRequest,
    user: CurrentUser,
    db: DatabaseSession,
) -> OnboardingCompleteResponse:
    workflow = OnboardingWorkflow(db)
    try:
        result = await workflow.complete(
            user_id=user.id,
            repo_full_name=data.repo_full_name,
            default_branch=data.default_branch,
        )
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=e.message)
    await db.commit()
    return OnboardingCompleteResponse(
        project_id=str(result.project_id),
        workspace_id=str(result.workspace_id),
        project_name=result.project_name,
    )
```

### Register Router

In `app/backend/src/organisms/api/app.py`, add:

```python
from organisms.api.routers.onboarding import router as onboarding_router
app.include_router(onboarding_router, prefix="/api/v1")
```

## Frontend: GitHub Callback Page

### File: `app/frontend/src/pages/GitHubCallbackPage.tsx`

This page receives the OAuth redirect from GitHub, extracts `code` and `state` from the URL query params, and sends them to the opener window via `postMessage`. This is the missing piece that makes the popup-based OAuth flow work.

```
URL: /auth/github/callback?code=XXX&state=YYY

Behavior:
1. Parse code + state from URL search params
2. postMessage({ type: "github-oauth-callback", code, state }) to window.opener
3. Close self (the popup)
4. If no opener (direct navigation), show a message
```

## Frontend: Onboarding Page

### File: `app/frontend/src/pages/OnboardingPage.tsx`

Multi-step wizard with 3 steps. Each step calls a backend API and renders the response. No business logic.

**Step 1: Connect GitHub**
- Reuses the existing `useGitHubConnection()` hook from `src/hooks/useGitHubConnection.ts` for the popup OAuth flow
- Shows a "Connect GitHub" button that calls `connect()` from the hook
- Polls `GET /api/v1/onboarding/status` after connection (or invalidates the onboarding status query on `connect()` resolve)
- When `has_github` becomes true, advances to step 2

**Step 2: Select Org**
- Calls `GET /api/v1/onboarding/github/orgs`
- Renders a list of orgs with avatars
- User clicks one to advance to step 3

**Step 3: Select Repo**
- Calls `GET /api/v1/onboarding/github/repos?org=X`
- Renders a searchable/filterable list of repos
- User clicks one, then confirms
- Calls `POST /api/v1/onboarding/complete` with `{ repo_full_name, default_branch }`
- On success, redirects to `/` (the main app)

### Styling

Follow the existing LoginPage pattern: centered card layout, design tokens from CSS variables, inline styles or Tailwind utility classes.

## Frontend: Onboarding Hook

### File: `app/frontend/src/hooks/useOnboarding.ts`

```typescript
// Encapsulates all onboarding API calls using react-query.
// Returns: status, orgs, repos, complete(), isLoading states.

function useOnboarding() {
  // GET /api/v1/onboarding/status
  const status = useQuery(...)

  // GET /api/v1/onboarding/github/orgs (enabled when has_github)
  const orgs = useQuery(...)

  // GET /api/v1/onboarding/github/repos?org=X (enabled when org selected)
  const repos = useQuery(...)

  // POST /api/v1/onboarding/complete
  const complete = useMutation(...)

  return { status, orgs, repos, complete, ... }
}
```

## Frontend: Route Changes

### File: `app/frontend/src/AppRouter.tsx`

```typescript
import { GitHubCallbackPage } from "@/pages/GitHubCallbackPage";
import { OnboardingPage } from "@/pages/OnboardingPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

### App.tsx: Onboarding Gate

In `App.tsx`, after auth check succeeds, add an onboarding check:

```typescript
function App() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  // After auth loads, check onboarding status
  const { data: onboardingStatus } = useQuery({
    queryKey: ["onboarding", "status"],
    queryFn: () => apiClient.get("/api/v1/onboarding/status"),
    enabled: isAuthenticated,
  });

  // Redirect to onboarding if needed
  useEffect(() => {
    if (onboardingStatus?.needs_onboarding) {
      navigate("/onboarding", { replace: true });
    }
  }, [onboardingStatus, navigate]);

  // ... rest of existing App
}
```

## Complete File Tree

```
app/backend/
  src/
    features/projects/
      models.py                                # MODIFY - add owner_id, make local_path nullable
      service.py                               # MODIFY - add get_by_owner()
      schemas/input.py                         # MODIFY - add owner_id, make local_path optional
      schemas/output.py                        # MODIFY - add owner_id, make local_path optional
    molecules/
      workflows/
        __init__.py                            # CREATE (empty)
        onboarding.py                          # CREATE - OnboardingWorkflow
    organisms/api/
      routers/onboarding.py                    # CREATE - onboarding router
      app.py                                   # MODIFY - register onboarding router
  alembic/versions/
    xxxx_add_project_owner_id.py               # CREATE - migration

app/frontend/
  src/
    pages/
      GitHubCallbackPage.tsx                   # CREATE - OAuth popup callback
      OnboardingPage.tsx                       # CREATE - multi-step wizard
    hooks/
      useOnboarding.ts                         # CREATE - onboarding API hook
    AppRouter.tsx                              # MODIFY - add callback + onboarding routes
    App.tsx                                    # MODIFY - add onboarding gate
```

## API Endpoints (New)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/onboarding/status` | Yes | Check if user needs onboarding |
| GET | `/api/v1/onboarding/github/orgs` | Yes | List user's GitHub orgs |
| GET | `/api/v1/onboarding/github/repos` | Yes | List repos for an org |
| POST | `/api/v1/onboarding/complete` | Yes | Create Project + Workspace |

## Environment Variables

No new environment variables required. This builds on the existing GitHub OAuth setup from SB-117.

## Implementation Order

| Step | What | Depends On | Files |
|------|------|------------|-------|
| 1 | Add `owner_id` to Project model + migration | -- | `models.py`, `schemas/input.py`, `schemas/output.py`, `service.py`, migration |
| 2 | Make `local_path` nullable on Project | Step 1 | Same migration, `models.py`, `schemas/input.py` |
| 3 | Create `OnboardingWorkflow` molecule | Steps 1-2 | `molecules/workflows/onboarding.py` |
| 4 | Create onboarding router | Step 3 | `organisms/api/routers/onboarding.py`, `app.py` |
| 5 | Create `GitHubCallbackPage` | -- | `pages/GitHubCallbackPage.tsx`, `AppRouter.tsx` |
| 6 | Create `useOnboarding` hook | Step 4 | `hooks/useOnboarding.ts` |
| 7 | Create `OnboardingPage` | Steps 5-6 | `pages/OnboardingPage.tsx` |
| 8 | Add onboarding gate to `App.tsx` | Step 7 | `App.tsx`, `AppRouter.tsx` |

Steps 1-4 (backend) and Step 5 (callback page) can proceed in parallel.

## Testing Strategy

### Backend Unit Tests

**`app/backend/__tests__/test_onboarding_workflow.py`**

- `test_get_status_no_github_no_project` -- needs_onboarding=True, has_github=False
- `test_get_status_has_github_no_project` -- needs_onboarding=True, has_github=True
- `test_get_status_has_project` -- needs_onboarding=False
- `test_list_github_orgs` -- returns personal + org accounts (mock httpx)
- `test_list_github_repos_personal` -- returns user's repos (mock httpx)
- `test_list_github_repos_org` -- returns org repos (mock httpx)
- `test_complete_creates_project_and_workspace` -- Project in active state, Workspace linked
- `test_complete_duplicate_project_name` -- raises OnboardingError
- `test_complete_no_github_token` -- raises OnboardingError

Markers: `@pytest.mark.unit`, `@pytest.mark.postgres` for DB tests.

### Backend API Tests

**`app/backend/__tests__/test_onboarding_router.py`**

- `test_status_unauthenticated` -- 401
- `test_status_needs_onboarding` -- 200, needs_onboarding=True
- `test_github_orgs_no_connection` -- 400
- `test_github_orgs_success` -- 200, list of orgs
- `test_github_repos_success` -- 200, list of repos
- `test_complete_success` -- 200, creates project + workspace
- `test_complete_duplicate` -- 400

### Frontend

Manual testing via `/verify` -- screenshot each onboarding step, verify popup OAuth flow, confirm redirect to app after completion.

## Open Questions

1. **Project name uniqueness**: Currently `Project.name` has `unique=True` globally. We use `repo_full_name` (e.g., `dug/backend`) as the project name to avoid collisions between users who have repos with the same short name. For a future iteration, consider `unique_together(name, owner_id)` if full-name collisions become an issue.

2. **Re-onboarding**: If a user wants to add a second repo later, they would use a different flow (project settings or a "new project" button). The onboarding flow is one-time for the first project only.

3. **Existing project router**: The `projects.py` router currently has no auth and no owner scoping. This should be updated in a follow-up to scope project CRUD to the authenticated user's projects.

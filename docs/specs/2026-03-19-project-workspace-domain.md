---
title: Project & Workspace Domain (EP-005)
date: 2026-03-19
status: draft
epic: EP-005
issues: [SB-027, SB-028, SB-029, SB-030, SB-031, SB-032, SB-033]
adrs: [ADR-004]
---

# Project & Workspace Domain

## Goal

Build the top-level ownership layer for stack-bench. A Project is the anchor entity that stacks, conversations, and workspaces hang off of. A Workspace is a git repository linked to a project. Projects use EventPattern (setup -> active -> archived state machine). Workspaces use BasePattern (no state machine -- either active or not). This domain must exist before EP-003 (Stack, Branch & PR) can be built, since Stack.project_id and Branch.workspace_id depend on these tables.

## Domain Model

```
Project (EventPattern)
  - name: str, required, unique, indexed, max 200
  - description: str, nullable
  - metadata_: dict, default {}
  - states: setup -> active -> archived

Workspace (BasePattern)
  - project_id: FK -> projects.id, required, indexed
  - name: str, required, max 200
  - repo_url: str, required, max 500
  - provider: str, required, max 20 (github | gitlab | bitbucket)
  - default_branch: str, required, max 200, default "main"
  - local_path: str, nullable, max 500
  - metadata_: dict, default {}
  - is_active: bool, default true, indexed
```

## Implementation Phases

| Phase | What | Issue | Depends On |
|-------|------|-------|------------|
| 1 | Project feature (model + schemas + service) | SB-027 | -- |
| 2 | Workspace feature (model + schemas + service) | SB-028 | SB-027 |
| 3 | Alembic migration for project + workspace | SB-033 | SB-027, SB-028 |
| 4 | Project + Workspace REST API routers | SB-029 | SB-027, SB-028 |
| 5 | Wire Conversation.project_id FK (optional) | SB-032 | SB-027 |
| 6 | Wire Stack.project_id FK (stub) | SB-030 | SB-027 |
| 7 | Wire Branch.workspace_id FK (stub) | SB-031 | SB-028 |

---

## Phase 1: Project Feature (SB-027)

### Files to Create

```
app/backend/src/features/projects/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
app/backend/__tests__/features/test_projects.py
```

### Model: `app/backend/src/features/projects/models.py`

```python
from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


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
```

### Schemas: `app/backend/src/features/projects/schemas/input.py`

```python
from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField


class ProjectCreate(BaseModel):
    name: str = PydanticField(..., min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    description: str | None = None
    metadata_: dict[str, Any] | None = None
```

### Schemas: `app/backend/src/features/projects/schemas/output.py`

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    name: str
    description: str | None = None
    metadata_: dict[str, Any]
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Schemas: `app/backend/src/features/projects/schemas/__init__.py`

Empty file.

### Service: `app/backend/src/features/projects/service.py`

```python
from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Project
from .schemas.input import ProjectCreate, ProjectUpdate


class ProjectService(BaseService[Project, ProjectCreate, ProjectUpdate]):
    model = Project

    async def get_by_name(self, db: AsyncSession, name: str) -> Project | None:
        result = await db.execute(select(Project).where(Project.name == name))
        return result.scalar_one_or_none()
```

### Exports: `app/backend/src/features/projects/__init__.py`

```python
from .models import Project
from .schemas.input import ProjectCreate, ProjectUpdate
from .schemas.output import ProjectResponse
from .service import ProjectService

__all__ = ["Project", "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectService"]
```

### Tests: `app/backend/__tests__/features/test_projects.py`

Test cases (all `@pytest.mark.unit`):

1. **test_project_model_fields** -- Verify model has `name`, `description`, `metadata_`, `state` attributes.
2. **test_project_pattern_config** -- Verify `Pattern.entity == "project"`, `reference_prefix == "PROJ"`, `initial_state == "setup"`, states dict has correct keys.
3. **test_project_state_machine** -- Create `Project()`, verify `state == "setup"`, `can_transition_to("active")`, transition to active, verify `can_transition_to("archived")`.
4. **test_project_invalid_transition** -- Verify `setup` cannot transition directly to `archived`.
5. **test_project_full_lifecycle** -- setup -> active -> archived, verify terminal state has no transitions.
6. **test_project_create_schema** -- Minimal: `ProjectCreate(name="my-project")`. Verify defaults.
7. **test_project_create_schema_full** -- All fields: name, description, metadata_.
8. **test_project_create_requires_name** -- `ProjectCreate()` raises `ValidationError`.
9. **test_project_create_rejects_empty_name** -- `ProjectCreate(name="")` raises `ValidationError`.
10. **test_project_update_schema** -- `ProjectUpdate(description="new desc")` allows partial.
11. **test_project_response_schema** -- Verify `from_attributes` config.
12. **test_project_service_model** -- `ProjectService().model is Project`.

---

## Phase 2: Workspace Feature (SB-028)

### Files to Create

```
app/backend/src/features/workspaces/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
app/backend/__tests__/features/test_workspaces.py
```

### Model: `app/backend/src/features/workspaces/models.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns import BasePattern, Field


class Workspace(BasePattern):
    __tablename__ = "workspaces"

    class Pattern:
        entity = "workspace"
        reference_prefix = "WKSP"
        track_changes = True

    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200)
    repo_url = Field(str, required=True, max_length=500)
    provider = Field(str, required=True, max_length=20, choices=["github", "gitlab", "bitbucket"])
    default_branch = Field(str, required=True, max_length=200, default="main")
    local_path = Field(str, nullable=True, max_length=500)
    metadata_ = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)
```

### Schemas: `app/backend/src/features/workspaces/schemas/input.py`

```python
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class WorkspaceCreate(BaseModel):
    project_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=200)
    repo_url: str = PydanticField(..., min_length=1, max_length=500)
    provider: Literal["github", "gitlab", "bitbucket"]
    default_branch: str = PydanticField("main", min_length=1, max_length=200)
    local_path: str | None = None
    metadata_: dict[str, Any] | None = None
    is_active: bool = True


class WorkspaceUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    repo_url: str | None = PydanticField(None, min_length=1, max_length=500)
    provider: Literal["github", "gitlab", "bitbucket"] | None = None
    default_branch: str | None = PydanticField(None, min_length=1, max_length=200)
    local_path: str | None = None
    metadata_: dict[str, Any] | None = None
    is_active: bool | None = None
```

### Schemas: `app/backend/src/features/workspaces/schemas/output.py`

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkspaceResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    repo_url: str
    provider: str
    default_branch: str
    local_path: str | None = None
    metadata_: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Schemas: `app/backend/src/features/workspaces/schemas/__init__.py`

Empty file.

### Service: `app/backend/src/features/workspaces/service.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Workspace
from .schemas.input import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService(BaseService[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID, active_only: bool = True
    ) -> list[Workspace]:
        query = select(Workspace).where(Workspace.project_id == project_id)
        if active_only:
            query = query.where(Workspace.is_active == True)  # noqa: E712
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_repo_url(self, db: AsyncSession, repo_url: str) -> Workspace | None:
        result = await db.execute(select(Workspace).where(Workspace.repo_url == repo_url))
        return result.scalar_one_or_none()
```

### Exports: `app/backend/src/features/workspaces/__init__.py`

```python
from .models import Workspace
from .schemas.input import WorkspaceCreate, WorkspaceUpdate
from .schemas.output import WorkspaceResponse
from .service import WorkspaceService

__all__ = ["Workspace", "WorkspaceCreate", "WorkspaceUpdate", "WorkspaceResponse", "WorkspaceService"]
```

### Tests: `app/backend/__tests__/features/test_workspaces.py`

Test cases (all `@pytest.mark.unit`):

1. **test_workspace_model_fields** -- Verify model has `project_id`, `name`, `repo_url`, `provider`, `default_branch`, `local_path`, `metadata_`, `is_active`.
2. **test_workspace_pattern_config** -- `Pattern.entity == "workspace"`, `reference_prefix == "WKSP"`.
3. **test_workspace_create_schema** -- Minimal: `WorkspaceCreate(project_id=uuid4(), name="backend", repo_url="https://github.com/org/repo", provider="github")`. Verify `default_branch == "main"`, `is_active == True`.
4. **test_workspace_create_schema_full** -- All fields including local_path and metadata_.
5. **test_workspace_create_requires_fields** -- Missing name, repo_url, or provider raises `ValidationError`.
6. **test_workspace_create_rejects_invalid_provider** -- `provider="svn"` raises `ValidationError`.
7. **test_workspace_update_schema** -- `WorkspaceUpdate(name="new-name")` allows partial.
8. **test_workspace_response_schema** -- Verify `from_attributes` config.
9. **test_workspace_service_model** -- `WorkspaceService().model is Workspace`.

---

## Phase 3: Alembic Migration (SB-033)

### File to Create

```
app/backend/alembic/versions/<auto>_add_projects_and_workspaces.py
```

Generate via: `cd app/backend && just migrate-gen "add projects and workspaces"`

The migration must create (in order, respecting FK dependencies):

**Table: `projects`**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| name | String(200) | NOT NULL |
| description | Text | nullable |
| metadata_ | JSON | nullable |
| state | String(50) | NOT NULL, comment "Current state in the state machine" |
| deleted_at | DateTime(tz) | nullable, comment "Timestamp when the record was soft deleted" |
| reference_number | String(50) | nullable, comment "Unique reference number" |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

Indexes:
- `ix_projects_name` on `name`, unique
- `ix_projects_state` on `state`
- `ix_projects_reference_number` on `reference_number`, unique

**Table: `workspaces`** (after projects, since FK dependency)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| project_id | UUID | NOT NULL, FK -> projects.id |
| name | String(200) | NOT NULL |
| repo_url | String(500) | NOT NULL |
| provider | String(20) | NOT NULL |
| default_branch | String(200) | NOT NULL |
| local_path | String(500) | nullable |
| metadata_ | JSON | nullable |
| is_active | Boolean | nullable (pattern default) |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

Indexes:
- `ix_workspaces_project_id` on `project_id`
- `ix_workspaces_is_active` on `is_active`

### File to Modify: `app/backend/src/features/__init__.py`

Add model imports for alembic discovery:

```python
from features.projects.models import Project  # noqa: F401
from features.workspaces.models import Workspace  # noqa: F401
```

### Downgrade

Drop `workspaces` first (FK dependency), then `projects`. Drop all indexes before each table.

---

## Phase 4: Project + Workspace REST API (SB-029)

### Files to Create

```
app/backend/src/organisms/api/routers/projects.py
app/backend/__tests__/organisms/test_project_routers.py
```

### Files to Modify

```
app/backend/src/organisms/api/dependencies.py   -- add project/workspace deps
app/backend/src/organisms/api/app.py             -- register new routers
app/backend/__tests__/organisms/test_routers.py  -- add route registration tests
```

### Router: `app/backend/src/organisms/api/routers/projects.py`

```python
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from features.projects import ProjectCreate, ProjectResponse, ProjectService, ProjectUpdate
from features.workspaces import WorkspaceCreate, WorkspaceResponse, WorkspaceService, WorkspaceUpdate
from organisms.api.dependencies import DatabaseSession

router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService()
workspace_service = WorkspaceService()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.create(db, data)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: DatabaseSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ProjectResponse]:
    items, _total = await project_service.list(db, offset=offset, limit=limit)
    return [ProjectResponse.model_validate(p) for p in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID, data: ProjectUpdate, db: DatabaseSession
) -> ProjectResponse:
    project = await project_service.update(db, project_id, data)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.transition_to("active")
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: UUID, db: DatabaseSession) -> ProjectResponse:
    project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.transition_to("archived")
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: DatabaseSession) -> None:
    await project_service.delete(db, project_id, soft=True)
    await db.commit()


# --- Workspace sub-routes (nested under project) ---


@router.post("/{project_id}/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    project_id: UUID, data: WorkspaceCreate, db: DatabaseSession
) -> WorkspaceResponse:
    # Override project_id from URL path
    create_data = data.model_copy(update={"project_id": project_id})
    workspace = await workspace_service.create(db, create_data)
    await db.commit()
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{project_id}/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(
    project_id: UUID,
    db: DatabaseSession,
    active_only: bool = Query(True),
) -> list[WorkspaceResponse]:
    items = await workspace_service.list_by_project(db, project_id, active_only=active_only)
    return [WorkspaceResponse.model_validate(w) for w in items]


@router.get(
    "/{project_id}/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def get_workspace(
    project_id: UUID, workspace_id: UUID, db: DatabaseSession
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.patch(
    "/{project_id}/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def update_workspace(
    project_id: UUID,
    workspace_id: UUID,
    data: WorkspaceUpdate,
    db: DatabaseSession,
) -> WorkspaceResponse:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    updated = await workspace_service.update(db, workspace_id, data)
    await db.commit()
    return WorkspaceResponse.model_validate(updated)


@router.delete("/{project_id}/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    project_id: UUID, workspace_id: UUID, db: DatabaseSession
) -> None:
    workspace = await workspace_service.get(db, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await workspace_service.delete(db, workspace_id, soft=False)
    await db.commit()
```

### Dependencies: `app/backend/src/organisms/api/dependencies.py`

No new dependency classes needed -- the router uses `DatabaseSession` directly with service instances (matching the simple pattern in the agents router). The existing `DatabaseSession` dependency is sufficient.

### App Registration: `app/backend/src/organisms/api/app.py`

Add to `create_app()`:

```python
from organisms.api.routers.projects import router as projects_router
app.include_router(projects_router, prefix="/api/v1")
```

### Tests: `app/backend/__tests__/organisms/test_project_routers.py`

Test cases (all `@pytest.mark.unit`):

1. **test_projects_router_registered** -- Verify `/projects` routes exist in `app.routes`.
2. **test_workspaces_router_registered** -- Verify `/projects/{project_id}/workspaces` routes exist.

### Modify: `app/backend/__tests__/organisms/test_routers.py`

Add:

3. **test_projects_router_registered** -- Same pattern as existing `test_conversations_router_registered`.

---

## Phase 5: Wire Conversation.project_id FK (SB-032)

This adds an optional `project_id` FK to the existing Conversation model.

### Files to Modify

```
app/backend/src/features/conversations/models.py
app/backend/src/features/conversations/schemas/input.py
app/backend/src/features/conversations/schemas/output.py
app/backend/__tests__/features/test_conversations.py
```

### Model Change: `app/backend/src/features/conversations/models.py`

Add field after existing fields:

```python
project_id = Field(UUID, foreign_key="projects.id", nullable=True, index=True)
```

### Schema Changes

**input.py** -- Add to `ConversationCreate`:
```python
project_id: UUID | None = None
```

**output.py** -- Add to `ConversationResponse`:
```python
project_id: UUID | None = None
```

### Migration

This column will be included in the Phase 3 migration (SB-033) as an `op.add_column` on the existing `conversations` table:

```python
op.add_column("conversations", sa.Column("project_id", sa.UUID(), nullable=True))
op.create_foreign_key(
    "fk_conversations_project_id",
    "conversations",
    "projects",
    ["project_id"],
    ["id"],
)
op.create_index(op.f("ix_conversations_project_id"), "conversations", ["project_id"], unique=False)
```

### Test Changes: `app/backend/__tests__/features/test_conversations.py`

Add:

1. **test_conversation_has_project_id** -- `assert hasattr(Conversation, "project_id")`.
2. **test_conversation_create_with_project_id** -- `ConversationCreate(agent_name="test", project_id=uuid4())` succeeds.
3. **test_conversation_create_without_project_id** -- `ConversationCreate(agent_name="test")` succeeds with `project_id is None`.

---

## Phase 6: Wire Stack.project_id FK Stub (SB-030)

This is a **stub** -- the Stack model does not exist yet (it comes in EP-003 / SB-014). This phase documents the contract so EP-003 can implement it.

### No Files Created or Modified

This is a documentation-only stub. When SB-014 (Stack feature) is implemented, the Stack model MUST include:

```python
project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
```

And the Stack create schema MUST include:

```python
project_id: UUID
```

### Acceptance Criteria

- The `projects` table exists with `id` column of type UUID (delivered by Phase 1).
- EP-003 issue SB-014 references this stub and includes `project_id` in the Stack model.

---

## Phase 7: Wire Branch.workspace_id FK Stub (SB-031)

This is a **stub** -- the Branch model does not exist yet (it comes in EP-003 / SB-015). This phase documents the contract so EP-003 can implement it.

### No Files Created or Modified

This is a documentation-only stub. When SB-015 (Branch feature) is implemented, the Branch model MUST include:

```python
workspace_id = Field(UUID, foreign_key="workspaces.id", required=True, index=True)
```

And the Branch create schema MUST include:

```python
workspace_id: UUID
```

### Acceptance Criteria

- The `workspaces` table exists with `id` column of type UUID (delivered by Phase 2).
- EP-003 issue SB-015 references this stub and includes `workspace_id` in the Branch model.

---

## Complete File Tree

### New Files

```
app/backend/src/features/projects/__init__.py           # Exports: Project, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectService
app/backend/src/features/projects/models.py              # EventPattern model with state machine
app/backend/src/features/projects/schemas/__init__.py    # Empty
app/backend/src/features/projects/schemas/input.py       # ProjectCreate, ProjectUpdate
app/backend/src/features/projects/schemas/output.py      # ProjectResponse
app/backend/src/features/projects/service.py             # ProjectService with get_by_name()

app/backend/src/features/workspaces/__init__.py          # Exports: Workspace, WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceService
app/backend/src/features/workspaces/models.py            # BasePattern model with project_id FK
app/backend/src/features/workspaces/schemas/__init__.py  # Empty
app/backend/src/features/workspaces/schemas/input.py     # WorkspaceCreate, WorkspaceUpdate
app/backend/src/features/workspaces/schemas/output.py    # WorkspaceResponse
app/backend/src/features/workspaces/service.py           # WorkspaceService with list_by_project(), get_by_repo_url()

app/backend/src/organisms/api/routers/projects.py        # REST router: project CRUD + workspace sub-routes
app/backend/alembic/versions/<auto>_add_projects_and_workspaces.py  # Migration

app/backend/__tests__/features/test_projects.py          # 12 unit tests
app/backend/__tests__/features/test_workspaces.py        # 9 unit tests
app/backend/__tests__/organisms/test_project_routers.py  # 2 unit tests
```

### Modified Files

```
app/backend/src/features/__init__.py                     # Add Project, Workspace model imports
app/backend/src/features/conversations/models.py         # Add project_id field
app/backend/src/features/conversations/schemas/input.py  # Add project_id to ConversationCreate
app/backend/src/features/conversations/schemas/output.py # Add project_id to ConversationResponse
app/backend/src/organisms/api/app.py                     # Register projects_router
app/backend/src/organisms/api/dependencies.py            # No changes needed (uses DatabaseSession directly)
app/backend/__tests__/features/test_conversations.py     # Add 3 tests for project_id
app/backend/__tests__/organisms/test_routers.py          # Add projects route registration test
```

---

## Key Design Decisions

1. **Project uses EventPattern** -- The setup -> active -> archived lifecycle is a genuine state machine. Projects start in setup while being configured, become active when ready, and can be archived.

2. **Workspace uses BasePattern** -- No state transitions needed. The `is_active` boolean is sufficient for soft-disabling workspaces.

3. **Workspaces nested under projects in API** -- `POST /projects/{id}/workspaces` rather than flat `/workspaces` endpoint. A workspace always belongs to a project, so the URL hierarchy reflects ownership.

4. **No molecule layer yet** -- Project and Workspace are simple CRUD entities. There is no cross-feature business logic at this stage. When EP-003 adds stacks and branches, a ProjectEntity molecule may emerge to coordinate project + stack + workspace operations.

5. **Conversation.project_id is optional** -- Conversations can exist without a project (backward compatibility with existing data). The FK is nullable.

6. **SB-030 and SB-031 are stubs** -- Stack and Branch models do not exist yet. We document the FK contract here so EP-003 implementors know what to reference.

7. **provider field uses choices constraint** -- `github | gitlab | bitbucket` as a string with choices rather than a separate enum table. This is simple and extensible.

8. **Single migration for all changes** -- One migration file for projects table, workspaces table, and conversations.project_id column. This keeps the migration chain clean.

---

## Testing Strategy

### Unit Tests (no DB required)

All tests use `@pytest.mark.unit`. The existing test patterns in this codebase test:
- Model field existence via `hasattr()`
- Pattern config via `Model.Pattern.xxx` assertions
- State machine via `transition_to()` and `can_transition_to()` on in-memory instances
- Schema validation via Pydantic construction and `ValidationError`
- Service model binding via `Service().model is Model`
- Router registration via `app.routes` inspection

### Test Counts

| Test File | Count | Focus |
|-----------|-------|-------|
| test_projects.py | 12 | Model, Pattern, state machine, schemas, service |
| test_workspaces.py | 9 | Model, Pattern, schemas, service |
| test_conversations.py (additions) | 3 | project_id field in model and schemas |
| test_project_routers.py | 2 | Route registration |
| test_routers.py (additions) | 1 | Route registration |
| **Total new tests** | **27** | |

---

## Open Questions

None. The domain model is well-defined in EP-005 and ADR-004. All pattern types and field definitions are straightforward applications of existing conventions.

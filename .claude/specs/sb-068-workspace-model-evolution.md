---
title: "SB-068: Workspace Model Evolution"
date: 2026-03-25
status: draft
issue: SB-068
epic: EP-011
depends_on: []
---

# SB-068: Workspace Model Evolution

## Goal

Upgrade the Workspace model from `BasePattern` to `EventPattern`, adding cloud provisioning fields and a state machine. This is the foundation for SB-069 (WorkspaceManager) and SB-070 (Workspace REST API).

## Current State

### Model (`app/backend/src/features/workspaces/models.py`)

```python
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

### Database Schema (from initial migration)

The `workspaces` table has columns: `project_id`, `name`, `repo_url`, `provider`, `default_branch`, `local_path`, `metadata_`, `is_active`, `created_at`, `updated_at`, `id`. It does **not** have `state`, `deleted_at`, or `reference_number` columns (those are EventPattern / ReferenceNumberMixin columns).

Note: The current model defines `reference_prefix = "WKSP"` in Pattern config, but since it extends `BasePattern` (not `EventPattern`), the `ReferenceNumberMixin` is not applied. The database table has no `reference_number` column.

### Service (`app/backend/src/features/workspaces/service.py`)

```python
class WorkspaceService(BaseService[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    async def list_by_project(self, db, project_id, active_only=True) -> list[Workspace]
    async def get_by_repo_url(self, db, repo_url) -> Workspace | None
```

### Schemas

**CreateInput** (`schemas/input.py`): `project_id`, `name`, `repo_url`, `provider`, `default_branch`, `local_path`, `metadata_`, `is_active`

**UpdateInput** (`schemas/input.py`): `name`, `repo_url`, `provider`, `default_branch`, `local_path`, `metadata_`, `is_active`

**Response** (`schemas/output.py`): `id`, `project_id`, `name`, `repo_url`, `provider`, `default_branch`, `local_path`, `metadata_`, `is_active`, `created_at`, `updated_at`

No **Summary** schema exists currently.

---

## Target State

### Model Changes

Change base class from `BasePattern` to `EventPattern`. This adds three columns automatically:
- `state` (str, max_length=50, required=True, indexed) -- from EventPattern
- `deleted_at` (datetime, nullable=True) -- from EventPattern
- `reference_number` (str, max_length=50, nullable=True, unique=True, indexed) -- from ReferenceNumberMixin (EventPattern inherits it)

Add six new cloud provisioning fields. Add state machine configuration.

```python
from uuid import UUID
from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Workspace(EventPattern):
    __tablename__ = "workspaces"

    class Pattern:
        entity = "workspace"
        reference_prefix = "WKSP"
        initial_state = "created"
        states = {
            "created": ["provisioning"],
            "provisioning": ["ready", "created"],       # can fail back to created
            "ready": ["stopped", "destroying"],
            "stopped": ["provisioning", "destroying"],   # can re-provision
            "destroying": ["destroyed"],
            "destroyed": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "provisioning": StatePhase.ACTIVE,
            "ready": StatePhase.ACTIVE,
            "stopped": StatePhase.ACTIVE,
            "destroying": StatePhase.ACTIVE,
            "destroyed": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    # Existing fields (unchanged)
    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200)
    repo_url = Field(str, required=True, max_length=500)
    provider = Field(str, required=True, max_length=20, choices=["github", "gitlab", "bitbucket"])
    default_branch = Field(str, required=True, max_length=200, default="main")
    local_path = Field(str, nullable=True, max_length=500)
    metadata_ = Field(dict, default=dict)
    is_active = Field(bool, default=True, index=True)

    # New cloud provisioning fields
    resource_profile = Field(str, max_length=20, default="standard")
    region = Field(str, max_length=50, default="northamerica-northeast2")
    cloud_run_service = Field(str, nullable=True, max_length=200)
    cloud_run_url = Field(str, nullable=True, max_length=500)
    gcs_bucket = Field(str, nullable=True, max_length=200)
    config = Field(dict, default=dict)
```

### Schema Changes

#### CreateInput (`schemas/input.py`)

Add three optional fields (all with defaults):

```python
class WorkspaceCreate(BaseModel):
    # ... existing fields unchanged ...
    resource_profile: Literal["light", "standard", "heavy"] = "standard"
    region: str = PydanticField("northamerica-northeast2", max_length=50)
    config: dict[str, Any] = PydanticField(default_factory=dict)
```

#### UpdateInput (`schemas/input.py`)

Add two optional fields:

```python
class WorkspaceUpdate(BaseModel):
    # ... existing fields unchanged ...
    resource_profile: Literal["light", "standard", "heavy"] | None = None
    config: dict[str, Any] | None = None
```

#### Response (`schemas/output.py`)

Add EventPattern fields and cloud fields:

```python
class WorkspaceResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    project_id: UUID
    name: str
    repo_url: str
    provider: str
    default_branch: str
    local_path: str | None = None
    metadata_: dict[str, Any]
    is_active: bool
    state: str
    resource_profile: str
    region: str
    cloud_run_service: str | None = None
    cloud_run_url: str | None = None
    gcs_bucket: str | None = None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

#### Summary (new schema in `schemas/output.py`)

```python
class WorkspaceSummary(BaseModel):
    id: UUID
    name: str
    state: str
    resource_profile: str
    cloud_run_url: str | None = None

    model_config = {"from_attributes": True}
```

### Service Changes

Add two new query methods. Keep existing methods. Note: there is no `EventService` in pattern-stack -- the service stays as `BaseService`. State transitions are performed directly on the model instance via `transition_to()` (not through the service).

```python
class WorkspaceService(BaseService[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    # Existing methods (unchanged)
    async def list_by_project(self, db, project_id, active_only=True) -> list[Workspace]: ...
    async def get_by_repo_url(self, db, repo_url) -> Workspace | None: ...

    # New methods
    async def get_by_project(self, db: AsyncSession, project_id: UUID) -> Workspace | None:
        """Get a single workspace for a project (convenience for 1:1 relationship)."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.project_id == project_id)
            .where(Workspace.deleted_at.is_(None))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_ready(self, db: AsyncSession, project_id: UUID) -> list[Workspace]:
        """List workspaces in 'ready' state for a project."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.project_id == project_id)
            .where(Workspace.state == "ready")
            .where(Workspace.deleted_at.is_(None))
        )
        return list(result.scalars().all())
```

### Module Exports (`__init__.py`)

Add `WorkspaceSummary` to exports:

```python
from .models import Workspace
from .schemas.input import WorkspaceCreate, WorkspaceUpdate
from .schemas.output import WorkspaceResponse, WorkspaceSummary
from .service import WorkspaceService

__all__ = ["Workspace", "WorkspaceCreate", "WorkspaceUpdate", "WorkspaceResponse", "WorkspaceSummary", "WorkspaceService"]
```

---

## Migration

### File

`app/backend/alembic/versions/<autogenerated>_add_workspace_provisioning.py`

Generate via: `cd app/backend && alembic revision --autogenerate -m "add workspace provisioning"`

The autogenerate should detect the model changes. However, it will NOT handle default backfills for existing rows, so manual SQL is needed.

### Columns to Add

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `state` | `String(50)` | NOT NULL | `'created'` | EventPattern field. Add with server_default, then drop server_default. |
| `deleted_at` | `DateTime(timezone=True)` | YES | NULL | EventPattern soft delete |
| `reference_number` | `String(50)` | YES | NULL | ReferenceNumberMixin. Nullable, unique, indexed. |
| `resource_profile` | `String(20)` | YES | `'standard'` | Add with server_default for backfill, then drop if desired |
| `region` | `String(50)` | YES | `'northamerica-northeast2'` | Add with server_default for backfill |
| `cloud_run_service` | `String(200)` | YES | NULL | |
| `cloud_run_url` | `String(500)` | YES | NULL | |
| `gcs_bucket` | `String(200)` | YES | NULL | |
| `config` | `JSON` | YES | `'{}'` | |

### Indexes to Add

| Index | Column | Unique |
|-------|--------|--------|
| `ix_workspaces_state` | `state` | No |
| `ix_workspaces_reference_number` | `reference_number` | Yes |

### Migration Implementation Notes

1. **`state` column**: Must be NOT NULL. Use `server_default='created'` so existing rows get the default. Then optionally remove the server_default (the Python model handles defaults via `initial_state`). Pattern: `op.add_column('workspaces', sa.Column('state', sa.String(50), nullable=False, server_default='created', comment='Current state in the state machine'))`.

2. **`reference_number` column**: Nullable, so no backfill needed. Existing rows will have NULL. New rows get reference numbers via `ensure_reference_number()` called by `BaseService.create()`.

3. **`resource_profile` and `region`**: Use server_default for backfill of existing rows. `op.add_column('workspaces', sa.Column('resource_profile', sa.String(20), nullable=True, server_default='standard'))`.

4. **`config`**: `op.add_column('workspaces', sa.Column('config', sa.JSON(), nullable=True))`.

5. After adding columns, create indexes on `state` and `reference_number`.

6. The downgrade should drop all new columns and indexes.

---

## Test Plan

### File

`app/backend/__tests__/features/test_workspaces.py`

### Existing Tests to Update

The existing tests remain valid. No changes needed to existing test functions -- they test field presence, schema validation, and service model binding, all of which are preserved.

### New Tests

```
test_workspace_model_has_event_pattern_fields
    Verify model has `state`, `deleted_at`, `reference_number` attributes.

test_workspace_model_has_cloud_fields
    Verify model has `resource_profile`, `region`, `cloud_run_service`,
    `cloud_run_url`, `gcs_bucket`, `config` attributes.

test_workspace_pattern_config_states
    Verify Pattern.initial_state == "created".
    Verify all 6 states are defined in Pattern.states.
    Verify Pattern.state_phases maps all states.

test_workspace_initial_state
    Create Workspace(), verify state == "created".

test_workspace_state_transition_created_to_provisioning
    Create Workspace(), transition_to("provisioning"), verify state.

test_workspace_state_transition_provisioning_to_ready
    Create Workspace(), transition through created -> provisioning -> ready.

test_workspace_state_transition_provisioning_fails_back_to_created
    Transition created -> provisioning -> created (failure case).

test_workspace_state_transition_ready_to_stopped
    Full path: created -> provisioning -> ready -> stopped.

test_workspace_state_transition_stopped_to_provisioning
    Re-provision: stopped -> provisioning.

test_workspace_state_transition_ready_to_destroying
    Teardown from ready: ready -> destroying -> destroyed.

test_workspace_state_transition_stopped_to_destroying
    Teardown from stopped: stopped -> destroying -> destroyed.

test_workspace_full_lifecycle
    Complete path: created -> provisioning -> ready -> stopped -> provisioning -> ready -> destroying -> destroyed.
    Verify get_allowed_transitions() == [] at destroyed.

test_workspace_invalid_transition_created_to_ready
    Verify created cannot skip to ready (must go through provisioning).

test_workspace_invalid_transition_destroyed_to_any
    Verify destroyed is a terminal state -- no transitions allowed.

test_workspace_invalid_transition_ready_to_created
    Verify ready cannot go back to created.

test_workspace_can_transition_to
    Verify can_transition_to() returns correct booleans.

test_workspace_soft_delete
    Create Workspace(), call soft_delete(), verify is_deleted == True.

test_workspace_restore
    Soft delete then restore, verify is_deleted == False.

test_workspace_create_schema_with_cloud_fields
    Create WorkspaceCreate with resource_profile, region, config.
    Verify defaults.

test_workspace_create_schema_defaults_cloud_fields
    Create WorkspaceCreate without cloud fields, verify defaults:
    resource_profile="standard", region="northamerica-northeast2", config={}.

test_workspace_create_rejects_invalid_resource_profile
    Verify Literal["light", "standard", "heavy"] validation.

test_workspace_update_schema_with_cloud_fields
    Create WorkspaceUpdate with resource_profile and config.

test_workspace_response_schema_has_cloud_fields
    Verify WorkspaceResponse has state, resource_profile, region,
    cloud_run_url, gcs_bucket, config fields.

test_workspace_summary_schema
    Verify WorkspaceSummary has id, name, state, resource_profile, cloud_run_url.
    Verify from_attributes config.
```

---

## File List

| Action | File |
|--------|------|
| Edit | `app/backend/src/features/workspaces/models.py` |
| Edit | `app/backend/src/features/workspaces/service.py` |
| Edit | `app/backend/src/features/workspaces/schemas/input.py` |
| Edit | `app/backend/src/features/workspaces/schemas/output.py` |
| Edit | `app/backend/src/features/workspaces/__init__.py` |
| Edit | `app/backend/__tests__/features/test_workspaces.py` |
| New | `app/backend/alembic/versions/<auto>_add_workspace_provisioning.py` |

---

## Implementation Order

1. **Model** (`models.py`) -- Change base class, add Pattern config, add cloud fields. This is the foundation.
2. **Schemas** (`schemas/input.py`, `schemas/output.py`) -- Add cloud fields to create/update inputs, response, and new summary schema.
3. **Service** (`service.py`) -- Add `get_by_project()` and `list_ready()` methods.
4. **Exports** (`__init__.py`) -- Add `WorkspaceSummary` to exports.
5. **Tests** (`test_workspaces.py`) -- Add all new tests. Run `just test` to verify.
6. **Migration** -- Generate with `alembic revision --autogenerate`, then review and adjust for server_defaults and backfills.

---

## Key Findings from Code Exploration

1. **No EventService**: Pattern-stack has only `BaseService`. There is no separate `EventService` class. The skill doc mentions `EventService` with `transition_state()`, but the actual package (`pattern_stack/atoms/patterns/services/__init__.py`) exports only `BaseService` and `PolymorphicService`. State transitions are done directly on model instances via `transition_to()`, not through the service.

2. **`reference_number` is nullable**: The `ReferenceNumberMixin` defines `reference_number` with `nullable=True` ("Allow NULL for tests and fixtures"). No backfill is required for existing rows. New rows get references via `ensure_reference_number()` called automatically by `BaseService.create()`.

3. **`transition_to()` is synchronous**: The method on EventPattern is a regular sync method, not async. It validates the transition, updates `self.state`, and emits events synchronously. Usage: `workspace.transition_to("provisioning")` then `await db.commit()`.

4. **`InvalidStateTransitionError` import path**: `from pattern_stack.atoms.patterns import InvalidStateTransitionError` (exported from `__init__.py`).

5. **Existing EventPattern models in codebase**: Project, Stack, Branch, PullRequest, Job, AgentRun, Task, Conversation, and others all use EventPattern already. The Project model (`features/projects/models.py`) is the closest reference -- same pattern of entity + reference_prefix + states + state_phases.

6. **Current workspaces table lacks EventPattern columns**: The initial migration creates `workspaces` without `state`, `deleted_at`, or `reference_number`. The migration must add all three.

7. **`deleted_at` usage in services**: The `ProjectService.get_by_owner()` filters with `_deleted_at.is_(None)`. The new workspace service methods (`get_by_project`, `list_ready`) should similarly filter out soft-deleted records.

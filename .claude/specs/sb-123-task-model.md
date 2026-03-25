---
title: Task model, service, and schemas
date: 2026-03-24
status: draft
issue: SB-123
branch: worktree-warm-crunching-lantern
depends_on: []
adrs: []
---

# Task Model, Service, and Schemas

## Goal

Build the core Task feature for the task management subsystem. Task is an EventPattern with a state machine modeling the full issue lifecycle (backlog through done/cancelled), external provider sync fields, and custom query methods. This is the central entity that TaskProject, Sprint, TaskComment, TaskTag, and TaskRelation all relate to.

## Domain Model

**Pattern type:** `EventPattern` -- Task has a multi-state lifecycle with transitions.

**Table name:** `tasks`

**Pattern config:**
- `entity = "task"`
- `reference_prefix = "TSK"`
- `initial_state = "backlog"`
- `emit_state_transitions = True`
- `track_changes = True`

**State machine:**
```
backlog -> ready -> in_progress -> in_review -> done
                                             -> cancelled
backlog -> cancelled
ready -> cancelled
in_progress -> cancelled
```

Full transitions map:
```python
states = {
    "backlog": ["ready", "cancelled"],
    "ready": ["in_progress", "cancelled"],
    "in_progress": ["in_review", "cancelled"],
    "in_review": ["done", "in_progress", "cancelled"],
    "done": [],
    "cancelled": [],
}
```

State phases:
```python
state_phases = {
    "backlog": StatePhase.INITIAL,
    "ready": StatePhase.PENDING,
    "in_progress": StatePhase.ACTIVE,
    "in_review": StatePhase.PENDING,
    "done": StatePhase.SUCCESS,
    "cancelled": StatePhase.FAILURE,
}
```

Note: `in_review` can transition back to `in_progress` (rework path).

**Domain fields:**

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `title` | `str` | required, max_length=500, index=True | Primary display field |
| `description` | `str` | nullable | Long-form, no max_length (Text) |
| `priority` | `str` | choices=["critical","high","medium","low","none"], default="none" | |
| `issue_type` | `str` | choices=["story","bug","task","spike","epic"], default="task" | |
| `work_phase` | `str` | choices=["design","build","test","deploy","review"], nullable | Current SDLC phase |
| `status_category` | `str` | choices=["todo","in_progress","done"], default="todo" | Coarse bucket for board columns |

**Foreign keys:**

| Field | Target | Constraints |
|-------|--------|-------------|
| `project_id` | `task_projects.id` | nullable, index=True |
| `assignee_id` | (UUID, no FK constraint) | nullable, index=True |
| `sprint_id` | `sprints.id` | nullable, index=True |

Note: `assignee_id` is a plain UUID without a foreign key constraint. The actor who owns the task may come from an external provider (GitHub user, Linear user) and will not necessarily exist in a local users table. This keeps the Task feature self-contained at the feature layer (no cross-feature FK to an actor table).

**External sync fields:**

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `external_id` | `str` | nullable, max_length=200, index=True | Provider's issue ID |
| `external_url` | `str` | nullable, max_length=500 | Link to issue in provider |
| `provider` | `str` | choices=["github","linear","local"], default="local" | Which system owns the canonical copy |
| `last_synced_at` | `datetime` | nullable | Timestamp of last sync from provider |

## File Tree

```
app/backend/src/features/tasks/
    __init__.py          # Exports: Task, TaskCreate, TaskUpdate, TaskResponse, TaskService
    models.py            # EventPattern model with state machine
    schemas/
        __init__.py      # Re-exports from input and output
        input.py         # TaskCreate, TaskUpdate (Pydantic BaseModel)
        output.py        # TaskResponse (Pydantic BaseModel, from_attributes)
    service.py           # BaseService[Task, TaskCreate, TaskUpdate] + custom queries

app/backend/__tests__/features/
    test_tasks.py        # Unit tests for model, schemas, service binding
```

## Interfaces

### models.py

```python
from uuid import UUID
from datetime import datetime
from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase

class Task(EventPattern):
    __tablename__ = "tasks"

    class Pattern:
        entity = "task"
        reference_prefix = "TSK"
        initial_state = "backlog"
        states = {
            "backlog": ["ready", "cancelled"],
            "ready": ["in_progress", "cancelled"],
            "in_progress": ["in_review", "cancelled"],
            "in_review": ["done", "in_progress", "cancelled"],
            "done": [],
            "cancelled": [],
        }
        state_phases = {
            "backlog": StatePhase.INITIAL,
            "ready": StatePhase.PENDING,
            "in_progress": StatePhase.ACTIVE,
            "in_review": StatePhase.PENDING,
            "done": StatePhase.SUCCESS,
            "cancelled": StatePhase.FAILURE,
        }
        emit_state_transitions = True
        track_changes = True

    # Domain fields
    title = Field(str, required=True, max_length=500, index=True)
    description = Field(str, nullable=True)
    priority = Field(str, default="none", choices=["critical", "high", "medium", "low", "none"])
    issue_type = Field(str, default="task", choices=["story", "bug", "task", "spike", "epic"])
    work_phase = Field(str, nullable=True, choices=["design", "build", "test", "deploy", "review"])
    status_category = Field(str, default="todo", choices=["todo", "in_progress", "done"])

    # Foreign keys
    project_id = Field(UUID, foreign_key="task_projects.id", nullable=True, index=True)
    assignee_id = Field(UUID, nullable=True, index=True)
    sprint_id = Field(UUID, foreign_key="sprints.id", nullable=True, index=True)

    # External sync
    external_id = Field(str, nullable=True, max_length=200, index=True)
    external_url = Field(str, nullable=True, max_length=500)
    provider = Field(str, default="local", choices=["github", "linear", "local"])
    last_synced_at = Field(datetime, nullable=True)
```

### schemas/input.py

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from pydantic import Field as PydanticField

class TaskCreate(BaseModel):
    title: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = PydanticField("none", pattern="^(critical|high|medium|low|none)$")
    issue_type: str = PydanticField("task", pattern="^(story|bug|task|spike|epic)$")
    work_phase: str | None = PydanticField(None, pattern="^(design|build|test|deploy|review)$")
    status_category: str = PydanticField("todo", pattern="^(todo|in_progress|done)$")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str = PydanticField("local", pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None

class TaskUpdate(BaseModel):
    title: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = PydanticField(None, pattern="^(critical|high|medium|low|none)$")
    issue_type: str | None = PydanticField(None, pattern="^(story|bug|task|spike|epic)$")
    work_phase: str | None = PydanticField(None, pattern="^(design|build|test|deploy|review)$")
    status_category: str | None = PydanticField(None, pattern="^(todo|in_progress|done)$")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = PydanticField(None, max_length=200)
    external_url: str | None = PydanticField(None, max_length=500)
    provider: str | None = PydanticField(None, pattern="^(github|linear|local)$")
    last_synced_at: datetime | None = None
```

### schemas/output.py

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class TaskResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    title: str
    description: str | None = None
    priority: str
    issue_type: str
    work_phase: str | None = None
    status_category: str
    state: str
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    sprint_id: UUID | None = None
    external_id: str | None = None
    external_url: str | None = None
    provider: str
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### service.py

```python
from uuid import UUID
from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Task
from .schemas.input import TaskCreate, TaskUpdate

_deleted_at = Task.__table__.c.deleted_at
_created_at = Task.__table__.c.created_at

class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    model = Task

    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_sprint(self, db: AsyncSession, sprint_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.sprint_id == sprint_id)
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_assignee(self, db: AsyncSession, assignee_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.assignee_id == assignee_id)
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def search_by_title(self, db: AsyncSession, query: str, limit: int = 20) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.title.ilike(f"%{query}%"))
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
```

## Test Plan

All tests use `@pytest.mark.unit` and run without a database (model instantiation, schema validation, service binding). This matches the existing pattern in `test_stacks.py`.

### Model tests
1. **test_task_model_fields** -- Verify all domain fields, FK fields, and sync fields exist on the model class.
2. **test_task_pattern_config** -- Verify Pattern inner class: entity, reference_prefix, initial_state, all state keys present.
3. **test_task_initial_state** -- Instantiate Task(), assert state is "backlog".
4. **test_task_state_machine_happy_path** -- Walk backlog -> ready -> in_progress -> in_review -> done, assert each transition succeeds.
5. **test_task_cancelled_from_each_state** -- Verify cancellation is reachable from backlog, ready, in_progress, in_review.
6. **test_task_invalid_transitions** -- Verify backlog cannot jump to in_progress, done, or in_review directly. Verify done and cancelled are terminal.
7. **test_task_rework_path** -- Verify in_review -> in_progress (rework), then back to in_review -> done.
8. **test_task_terminal_states** -- Verify done and cancelled have no allowed transitions.

### Schema tests
9. **test_task_create_minimal** -- TaskCreate with only title, verify defaults (priority="none", issue_type="task", provider="local", status_category="todo").
10. **test_task_create_full** -- TaskCreate with all fields populated, verify round-trip.
11. **test_task_create_requires_title** -- Omitting title raises ValidationError.
12. **test_task_create_rejects_empty_title** -- Empty string title raises ValidationError.
13. **test_task_create_rejects_invalid_priority** -- Invalid priority value raises ValidationError.
14. **test_task_create_rejects_invalid_provider** -- Invalid provider value raises ValidationError.
15. **test_task_update_partial** -- TaskUpdate with only title set, rest are None.
16. **test_task_response_from_attributes** -- Verify model_config has from_attributes=True.

### Service tests
17. **test_task_service_model** -- Verify TaskService().model is Task.

## Implementation Steps

| Step | What | Notes |
|------|------|-------|
| 1 | Create `app/backend/src/features/tasks/` directory structure | models.py, service.py, schemas/{__init__,input,output}.py, __init__.py |
| 2 | Implement `models.py` | EventPattern, state machine, all fields per spec above |
| 3 | Implement `schemas/input.py` | TaskCreate, TaskUpdate with Pydantic validation |
| 4 | Implement `schemas/output.py` | TaskResponse with from_attributes |
| 5 | Implement `schemas/__init__.py` | Re-export schemas |
| 6 | Implement `service.py` | BaseService + 4 custom query methods |
| 7 | Implement `__init__.py` | Export all public symbols |
| 8 | Write `__tests__/features/test_tasks.py` | All 17 test cases |
| 9 | Run `just quality` from `app/backend/` | Verify lint, typecheck, tests pass |

## Key Design Decisions

1. **EventPattern over BasePattern** -- Task has a multi-state lifecycle. EventPattern provides `state`, `transition_to()`, `can_transition_to()`, soft delete via `deleted_at`, and state transition event emission.

2. **assignee_id as plain UUID (no FK constraint)** -- Assignees may be external actors from GitHub or Linear that do not exist in any local table. Adding a FK would require syncing all external users into a local actor table, which is out of scope for this feature. The molecule layer can resolve assignee identities.

3. **status_category as denormalized field** -- Provides a coarse "todo/in_progress/done" bucket for board column grouping without requiring the UI to interpret the full state machine. This is a common pattern in task trackers (e.g., Linear's status categories, Jira's status categories).

4. **Regex patterns on schema enum fields** -- Uses `pattern=` in Pydantic Field rather than Python `Literal` types. This matches the `choices=` constraint on the model Field and keeps validation consistent. An alternative would be `Literal["critical", "high", ...]` -- either works, but pattern is more concise for many enum fields.

5. **Soft-delete filtering in custom queries** -- All custom service methods filter by `_deleted_at.is_(None)`, matching the convention established in `StackService`.

6. **No cross-feature imports** -- Task references `task_projects.id` and `sprints.id` via string FK references only. No Python imports from other features. Composition happens at the molecule layer.

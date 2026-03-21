---
title: Stack, Branch & PR Domain (EP-003)
date: 2026-03-19
status: draft
epic: EP-003
issues: [SB-014, SB-015, SB-016, SB-017, SB-018, SB-019, SB-020]
depends_on: [EP-005]
adrs: [ADR-004]
---

# Stack, Branch & PR Domain

## Goal

Build the core workflow primitives for stacked PRs: Stack, Branch, and PullRequest as first-class domain entities in the backend. These model the three-tier architecture (local git -> stack-bench private workspace -> GitHub PRs). Stacks belong to Projects and form a DAG via `base_branch_id`. Branches belong to Stacks and Workspaces, enabling cross-repo stacking. PullRequests have a 1:1 relationship with Branches and exist in the private workspace before any GitHub PR is created. A StackProvider protocol with StackCLIAdapter wraps the existing `stack` CLI binary for git operations.

This spec assumes EP-005 (Project & Workspace Domain) is already implemented, providing the `projects`, `workspaces`, and `worktrees` tables with their models, services, and schemas. EP-005 includes a Worktree model (SB-034) that has a nullable `branch_id` FK pointing back to the `branches` table defined here. That FK is deferred until EP-003 tables exist -- EP-005 creates the column without the constraint, and the EP-003 migration (Phase 7) adds the FK.

## Domain Model

```
Stack (EventPattern)
  - project_id: UUID FK -> projects.id, required, indexed
  - name: str, required, max 200, indexed
  - base_branch_id: UUID FK -> branches.id, nullable, indexed
  - trunk: str, required, max 200, default "main"
  - states: draft -> active -> submitted -> merged -> closed

Branch (EventPattern)
  - stack_id: UUID FK -> stacks.id, required, indexed
  - workspace_id: UUID FK -> workspaces.id, required, indexed
  - name: str, required, max 500 (git branch names can be long)
  - position: int, required, min 1
  - head_sha: str, nullable, max 40
  - states: created -> pushed -> reviewing -> ready -> submitted -> merged

PullRequest (EventPattern)
  - branch_id: UUID FK -> branches.id, required, unique (1:1)
  - external_id: int, nullable (GitHub PR number, null until submitted)
  - external_url: str, nullable, max 500
  - title: str, required, max 500
  - description: str, nullable (Text, no max_length)
  - review_notes: str, nullable (Text, private markup -- the staging layer)
  - states: draft -> open -> approved -> merged / closed
```

Relationships:
- Stack -> Project: many-to-one via `project_id`
- Stack -> Branch (base): optional many-to-one via `base_branch_id` (null = starts from trunk)
- Branch -> Stack: many-to-one via `stack_id`
- Branch -> Workspace: many-to-one via `workspace_id`
- Branch <- Worktree: one-to-many (Worktree.branch_id FK, defined in EP-005 SB-034, nullable)
- PullRequest -> Branch: one-to-one via `branch_id` (unique constraint)
- Stack DAG: `Stack.base_branch_id` -> any Branch in any stack, forming a directed acyclic graph

Note: The Worktree model is defined in EP-005 (SB-034), not in this spec. It has a nullable `branch_id` FK -> `branches.id`. A Branch can have zero or more Worktrees (local checkouts). The Worktree bridges the "local git" tier to the private workspace tier. EP-003 does not define or modify the Worktree model, but the migration (Phase 7) adds the deferred FK constraint from `worktrees.branch_id` to `branches.id`.

## Implementation Phases

| Phase | What | Issue | Depends On |
|-------|------|-------|------------|
| 1 | Stack feature (model + schemas + service) | SB-014 | EP-005 (SB-027) |
| 2 | Branch feature (model + schemas + service) | SB-015 | SB-014, EP-005 (SB-028) |
| 3 | PullRequest feature (model + schemas + service) | SB-016 | SB-015 |
| 4 | Stack molecule (StackEntity + StackAPI facade) | SB-017 | SB-014, SB-015, SB-016 |
| 5 | StackProvider protocol + StackCLIAdapter | SB-018 | SB-017 |
| 6 | REST API routers (stacks, branches, PRs) | SB-019 | SB-017 |
| 7 | Alembic migration + seed data | SB-020 | SB-014, SB-015, SB-016 |

---

## Phase 1: Stack Feature (SB-014)

### Files to Create

```
app/backend/src/features/stacks/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
app/backend/__tests__/features/test_stacks.py
```

### Model: `app/backend/src/features/stacks/models.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class Stack(EventPattern):
    __tablename__ = "stacks"

    class Pattern:
        entity = "stack"
        reference_prefix = "STK"
        initial_state = "draft"
        states = {
            "draft": ["active"],
            "active": ["submitted", "closed"],
            "submitted": ["merged", "closed"],
            "merged": [],
            "closed": [],
        }
        state_phases = {
            "draft": StatePhase.INITIAL,
            "active": StatePhase.ACTIVE,
            "submitted": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "closed": StatePhase.ARCHIVED,
        }
        emit_state_transitions = True
        track_changes = True

    project_id = Field(UUID, foreign_key="projects.id", required=True, index=True)
    name = Field(str, required=True, max_length=200, index=True)
    base_branch_id = Field(UUID, foreign_key="branches.id", nullable=True, index=True)
    trunk = Field(str, required=True, max_length=200, default="main")
```

Note on `base_branch_id`: This FK references `branches.id`, but the `branches` table is created in Phase 2 (SB-015). The migration (Phase 7) must create `stacks` first without the FK, then `branches`, then add the FK via `ALTER TABLE`. See Phase 7 for details.

### Schemas: `app/backend/src/features/stacks/schemas/input.py`

```python
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class StackCreate(BaseModel):
    project_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=200)
    base_branch_id: UUID | None = None
    trunk: str = PydanticField("main", min_length=1, max_length=200)


class StackUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=200)
    base_branch_id: UUID | None = None
    trunk: str | None = PydanticField(None, min_length=1, max_length=200)
```

### Schemas: `app/backend/src/features/stacks/schemas/output.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StackResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    project_id: UUID
    name: str
    base_branch_id: UUID | None = None
    trunk: str
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Schemas: `app/backend/src/features/stacks/schemas/__init__.py`

Empty file.

### Service: `app/backend/src/features/stacks/service.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Stack
from .schemas.input import StackCreate, StackUpdate


class StackService(BaseService[Stack, StackCreate, StackUpdate]):
    model = Stack

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID
    ) -> list[Stack]:
        """Get all stacks for a project."""
        result = await db.execute(
            select(Stack)
            .where(Stack.project_id == project_id)
            .where(Stack.deleted_at.is_(None))
            .order_by(Stack.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, db: AsyncSession, project_id: UUID, name: str
    ) -> Stack | None:
        """Get a stack by project and name."""
        result = await db.execute(
            select(Stack)
            .where(Stack.project_id == project_id)
            .where(Stack.name == name)
            .where(Stack.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_dependents(
        self, db: AsyncSession, branch_id: UUID
    ) -> list[Stack]:
        """Get stacks that depend on a given branch (via base_branch_id)."""
        result = await db.execute(
            select(Stack)
            .where(Stack.base_branch_id == branch_id)
            .where(Stack.deleted_at.is_(None))
        )
        return list(result.scalars().all())
```

### Exports: `app/backend/src/features/stacks/__init__.py`

```python
from .models import Stack
from .schemas.input import StackCreate, StackUpdate
from .schemas.output import StackResponse
from .service import StackService

__all__ = ["Stack", "StackCreate", "StackUpdate", "StackResponse", "StackService"]
```

### Tests: `app/backend/__tests__/features/test_stacks.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stack_model_fields** -- Verify model has `project_id`, `name`, `base_branch_id`, `trunk`, `state` attributes via `hasattr()`.
2. **test_stack_pattern_config** -- Verify `Pattern.entity == "stack"`, `reference_prefix == "STK"`, `initial_state == "draft"`, states dict has correct keys (`draft`, `active`, `submitted`, `merged`, `closed`).
3. **test_stack_state_machine** -- Create `Stack()`, verify `state == "draft"`, `can_transition_to("active")`, transition to active, verify can go to `submitted` and `closed`.
4. **test_stack_invalid_transition** -- Verify `draft` cannot transition to `submitted`, `merged`, or `closed` directly.
5. **test_stack_full_lifecycle** -- `draft -> active -> submitted -> merged`, verify `merged` is terminal.
6. **test_stack_closed_path** -- `draft -> active -> closed`, verify `closed` is terminal.
7. **test_stack_submitted_to_closed** -- `draft -> active -> submitted -> closed`, verify `closed` is terminal.
8. **test_stack_create_schema** -- Minimal: `StackCreate(project_id=uuid4(), name="my-stack")`. Verify `trunk == "main"`, `base_branch_id is None`.
9. **test_stack_create_schema_full** -- All fields: `project_id`, `name`, `base_branch_id`, `trunk`.
10. **test_stack_create_requires_fields** -- `StackCreate()` raises `ValidationError`. `StackCreate(project_id=uuid4())` raises `ValidationError` (missing name).
11. **test_stack_create_rejects_empty_name** -- `StackCreate(project_id=uuid4(), name="")` raises `ValidationError`.
12. **test_stack_update_schema** -- `StackUpdate(name="new-name")` allows partial. All fields optional.
13. **test_stack_response_schema** -- Verify `from_attributes` config is True.
14. **test_stack_service_model** -- `StackService().model is Stack`.

---

## Phase 2: Branch Feature (SB-015)

### Files to Create

```
app/backend/src/features/branches/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
app/backend/__tests__/features/test_branches.py
```

### Model: `app/backend/src/features/branches/models.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase
from sqlalchemy import UniqueConstraint


class Branch(EventPattern):
    __tablename__ = "branches"

    __table_args__ = (
        UniqueConstraint("stack_id", "position", name="uq_branch_stack_position"),
    )

    class Pattern:
        entity = "branch"
        reference_prefix = "BR"
        initial_state = "created"
        states = {
            "created": ["pushed"],
            "pushed": ["reviewing"],
            "reviewing": ["ready"],
            "ready": ["submitted"],
            "submitted": ["merged"],
            "merged": [],
        }
        state_phases = {
            "created": StatePhase.INITIAL,
            "pushed": StatePhase.ACTIVE,
            "reviewing": StatePhase.ACTIVE,
            "ready": StatePhase.PENDING,
            "submitted": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
        }
        emit_state_transitions = True
        track_changes = True

    stack_id = Field(UUID, foreign_key="stacks.id", required=True, index=True)
    workspace_id = Field(UUID, foreign_key="workspaces.id", required=True, index=True)
    name = Field(str, required=True, max_length=500)
    position = Field(int, required=True, min=1)
    head_sha = Field(str, nullable=True, max_length=40)
```

The `UniqueConstraint("stack_id", "position")` ensures no two branches in the same stack share a position. This follows the same pattern used by `Message` (`UniqueConstraint("conversation_id", "sequence")`).

### Schemas: `app/backend/src/features/branches/schemas/input.py`

```python
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class BranchCreate(BaseModel):
    stack_id: UUID
    workspace_id: UUID
    name: str = PydanticField(..., min_length=1, max_length=500)
    position: int = PydanticField(..., ge=1)
    head_sha: str | None = PydanticField(None, max_length=40)


class BranchUpdate(BaseModel):
    name: str | None = PydanticField(None, min_length=1, max_length=500)
    position: int | None = PydanticField(None, ge=1)
    head_sha: str | None = PydanticField(None, max_length=40)
    workspace_id: UUID | None = None
```

### Schemas: `app/backend/src/features/branches/schemas/output.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BranchResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    stack_id: UUID
    workspace_id: UUID
    name: str
    position: int
    head_sha: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Schemas: `app/backend/src/features/branches/schemas/__init__.py`

Empty file.

### Service: `app/backend/src/features/branches/service.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Branch
from .schemas.input import BranchCreate, BranchUpdate


class BranchService(BaseService[Branch, BranchCreate, BranchUpdate]):
    model = Branch

    async def list_by_stack(
        self, db: AsyncSession, stack_id: UUID
    ) -> list[Branch]:
        """Get all branches for a stack, ordered by position."""
        result = await db.execute(
            select(Branch)
            .where(Branch.stack_id == stack_id)
            .where(Branch.deleted_at.is_(None))
            .order_by(Branch.position)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, db: AsyncSession, stack_id: UUID, name: str
    ) -> Branch | None:
        """Get a branch by stack and git branch name."""
        result = await db.execute(
            select(Branch)
            .where(Branch.stack_id == stack_id)
            .where(Branch.name == name)
            .where(Branch.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_max_position(
        self, db: AsyncSession, stack_id: UUID
    ) -> int:
        """Get the highest position in a stack (0 if no branches)."""
        from sqlalchemy import func

        result = await db.execute(
            select(func.coalesce(func.max(Branch.position), 0)).where(
                Branch.stack_id == stack_id
            )
        )
        return result.scalar_one()

    async def list_by_workspace(
        self, db: AsyncSession, workspace_id: UUID
    ) -> list[Branch]:
        """Get all branches in a workspace."""
        result = await db.execute(
            select(Branch)
            .where(Branch.workspace_id == workspace_id)
            .where(Branch.deleted_at.is_(None))
            .order_by(Branch.created_at)
        )
        return list(result.scalars().all())
```

### Exports: `app/backend/src/features/branches/__init__.py`

```python
from .models import Branch
from .schemas.input import BranchCreate, BranchUpdate
from .schemas.output import BranchResponse
from .service import BranchService

__all__ = ["Branch", "BranchCreate", "BranchUpdate", "BranchResponse", "BranchService"]
```

### Tests: `app/backend/__tests__/features/test_branches.py`

Test cases (all `@pytest.mark.unit`):

1. **test_branch_model_fields** -- Verify model has `stack_id`, `workspace_id`, `name`, `position`, `head_sha`, `state` attributes.
2. **test_branch_pattern_config** -- Verify `Pattern.entity == "branch"`, `reference_prefix == "BR"`, `initial_state == "created"`, states dict has correct keys (`created`, `pushed`, `reviewing`, `ready`, `submitted`, `merged`).
3. **test_branch_state_machine** -- Create `Branch()`, verify `state == "created"`, `can_transition_to("pushed")`, transition to pushed, verify can go to `reviewing`.
4. **test_branch_invalid_transition** -- Verify `created` cannot transition to `reviewing`, `ready`, `submitted`, or `merged`.
5. **test_branch_full_lifecycle** -- `created -> pushed -> reviewing -> ready -> submitted -> merged`, verify `merged` is terminal.
6. **test_branch_create_schema** -- Minimal: `BranchCreate(stack_id=uuid4(), workspace_id=uuid4(), name="user/stack/1-feat", position=1)`. Verify `head_sha is None`.
7. **test_branch_create_schema_with_sha** -- Include `head_sha="a" * 40`.
8. **test_branch_create_requires_fields** -- Missing `stack_id`, `workspace_id`, `name`, or `position` raises `ValidationError`.
9. **test_branch_create_rejects_zero_position** -- `position=0` raises `ValidationError`.
10. **test_branch_create_rejects_empty_name** -- `name=""` raises `ValidationError`.
11. **test_branch_update_schema** -- `BranchUpdate(head_sha="b" * 40)` allows partial. All fields optional.
12. **test_branch_response_schema** -- Verify `from_attributes` config is True.
13. **test_branch_service_model** -- `BranchService().model is Branch`.

---

## Phase 3: PullRequest Feature (SB-016)

### Files to Create

```
app/backend/src/features/pull_requests/
  __init__.py
  models.py
  schemas/
    __init__.py
    input.py
    output.py
  service.py
app/backend/__tests__/features/test_pull_requests.py
```

### Model: `app/backend/src/features/pull_requests/models.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns import EventPattern, Field, StatePhase


class PullRequest(EventPattern):
    __tablename__ = "pull_requests"

    class Pattern:
        entity = "pull_request"
        reference_prefix = "PR"
        initial_state = "draft"
        states = {
            "draft": ["open"],
            "open": ["approved", "closed"],
            "approved": ["merged", "closed"],
            "merged": [],
            "closed": ["open"],
        }
        state_phases = {
            "draft": StatePhase.INITIAL,
            "open": StatePhase.ACTIVE,
            "approved": StatePhase.PENDING,
            "merged": StatePhase.SUCCESS,
            "closed": StatePhase.FAILURE,
        }
        emit_state_transitions = True
        track_changes = True

    branch_id = Field(UUID, foreign_key="branches.id", required=True, unique=True, index=True)
    external_id = Field(int, nullable=True)
    external_url = Field(str, nullable=True, max_length=500)
    title = Field(str, required=True, max_length=500)
    description = Field(str, nullable=True)
    review_notes = Field(str, nullable=True)
```

Design notes:
- `branch_id` is `unique=True` to enforce the 1:1 relationship with Branch. The `Field(..., unique=True)` pattern creates the unique constraint at the column level.
- `description` and `review_notes` use `Field(str, nullable=True)` without `max_length`, which maps to `Text` in SQLAlchemy (unlimited length).
- `closed -> open` transition allows reopening a closed PR.
- `external_id` and `external_url` are both nullable because the PullRequest exists in the private workspace before any GitHub PR is created.

### Schemas: `app/backend/src/features/pull_requests/schemas/input.py`

```python
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PydanticField


class PullRequestCreate(BaseModel):
    branch_id: UUID
    title: str = PydanticField(..., min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None
    external_id: int | None = None
    external_url: str | None = PydanticField(None, max_length=500)


class PullRequestUpdate(BaseModel):
    title: str | None = PydanticField(None, min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None
    external_id: int | None = None
    external_url: str | None = PydanticField(None, max_length=500)
```

### Schemas: `app/backend/src/features/pull_requests/schemas/output.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PullRequestResponse(BaseModel):
    id: UUID
    reference_number: str | None = None
    branch_id: UUID
    external_id: int | None = None
    external_url: str | None = None
    title: str
    description: str | None = None
    review_notes: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Schemas: `app/backend/src/features/pull_requests/schemas/__init__.py`

Empty file.

### Service: `app/backend/src/features/pull_requests/service.py`

```python
from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PullRequest
from .schemas.input import PullRequestCreate, PullRequestUpdate


class PullRequestService(BaseService[PullRequest, PullRequestCreate, PullRequestUpdate]):
    model = PullRequest

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID
    ) -> PullRequest | None:
        """Get the pull request for a branch (1:1 relationship)."""
        result = await db.execute(
            select(PullRequest)
            .where(PullRequest.branch_id == branch_id)
            .where(PullRequest.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self, db: AsyncSession, external_id: int
    ) -> PullRequest | None:
        """Get a pull request by its GitHub PR number."""
        result = await db.execute(
            select(PullRequest)
            .where(PullRequest.external_id == external_id)
            .where(PullRequest.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
```

### Exports: `app/backend/src/features/pull_requests/__init__.py`

```python
from .models import PullRequest
from .schemas.input import PullRequestCreate, PullRequestUpdate
from .schemas.output import PullRequestResponse
from .service import PullRequestService

__all__ = [
    "PullRequest",
    "PullRequestCreate",
    "PullRequestUpdate",
    "PullRequestResponse",
    "PullRequestService",
]
```

### Tests: `app/backend/__tests__/features/test_pull_requests.py`

Test cases (all `@pytest.mark.unit`):

1. **test_pull_request_model_fields** -- Verify model has `branch_id`, `external_id`, `external_url`, `title`, `description`, `review_notes`, `state` attributes.
2. **test_pull_request_pattern_config** -- Verify `Pattern.entity == "pull_request"`, `reference_prefix == "PR"`, `initial_state == "draft"`, states dict has correct keys (`draft`, `open`, `approved`, `merged`, `closed`).
3. **test_pull_request_state_machine** -- Create `PullRequest()`, verify `state == "draft"`, `can_transition_to("open")`, transition to open, verify can go to `approved` and `closed`.
4. **test_pull_request_invalid_transition** -- Verify `draft` cannot transition to `approved`, `merged`, or `closed`.
5. **test_pull_request_full_lifecycle** -- `draft -> open -> approved -> merged`, verify `merged` is terminal.
6. **test_pull_request_closed_path** -- `draft -> open -> closed`, verify `closed` can reopen to `open`.
7. **test_pull_request_reopen** -- `draft -> open -> closed -> open`, verify transition succeeds.
8. **test_pull_request_approved_to_closed** -- `draft -> open -> approved -> closed`, verify allowed.
9. **test_pull_request_create_schema** -- Minimal: `PullRequestCreate(branch_id=uuid4(), title="Add feature X")`. Verify `external_id is None`, `description is None`, `review_notes is None`.
10. **test_pull_request_create_schema_full** -- All fields: `branch_id`, `title`, `description`, `review_notes`, `external_id`, `external_url`.
11. **test_pull_request_create_requires_fields** -- Missing `branch_id` or `title` raises `ValidationError`.
12. **test_pull_request_create_rejects_empty_title** -- `title=""` raises `ValidationError`.
13. **test_pull_request_update_schema** -- `PullRequestUpdate(title="Updated title")` allows partial. All fields optional.
14. **test_pull_request_update_review_notes** -- `PullRequestUpdate(review_notes="## Feedback\n- Fix error handling")` succeeds.
15. **test_pull_request_response_schema** -- Verify `from_attributes` config is True.
16. **test_pull_request_service_model** -- `PullRequestService().model is PullRequest`.

---

## Phase 4: Stack Molecule (SB-017)

### Files to Create

```
app/backend/src/molecules/entities/stack_entity.py
app/backend/src/molecules/apis/stack_api.py
app/backend/__tests__/molecules/test_stack_entity.py
app/backend/__tests__/molecules/test_stack_api.py
```

### Files to Modify

```
app/backend/src/molecules/exceptions.py   -- add StackNotFoundError, BranchNotFoundError, PullRequestNotFoundError
```

### Exceptions: `app/backend/src/molecules/exceptions.py`

Add after existing exceptions:

```python
class StackNotFoundError(MoleculeError):
    def __init__(self, stack_id: UUID) -> None:
        super().__init__(f"Stack {stack_id} not found")
        self.stack_id = stack_id


class BranchNotFoundError(MoleculeError):
    def __init__(self, branch_id: UUID) -> None:
        super().__init__(f"Branch {branch_id} not found")
        self.branch_id = branch_id


class PullRequestNotFoundError(MoleculeError):
    def __init__(self, pull_request_id: UUID) -> None:
        super().__init__(f"PullRequest {pull_request_id} not found")
        self.pull_request_id = pull_request_id


class StackCycleError(MoleculeError):
    def __init__(self, stack_id: UUID, base_branch_id: UUID) -> None:
        super().__init__(
            f"Setting base_branch_id={base_branch_id} on stack {stack_id} would create a cycle"
        )
        self.stack_id = stack_id
        self.base_branch_id = base_branch_id
```

### Entity: `app/backend/src/molecules/entities/stack_entity.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from features.branches.schemas.input import BranchCreate, BranchUpdate
from features.branches.service import BranchService
from features.pull_requests.schemas.input import PullRequestCreate, PullRequestUpdate
from features.pull_requests.service import PullRequestService
from features.stacks.schemas.input import StackCreate, StackUpdate
from features.stacks.service import StackService
from molecules.exceptions import (
    BranchNotFoundError,
    PullRequestNotFoundError,
    StackCycleError,
    StackNotFoundError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.branches.models import Branch
    from features.pull_requests.models import PullRequest
    from features.stacks.models import Stack


class StackEntity:
    """Domain aggregate for stack + branch + pull request lifecycle.

    Coordinates the three features into a single domain concept.
    The stack owns the branches, and each branch optionally owns a pull request.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stack_service = StackService()
        self.branch_service = BranchService()
        self.pr_service = PullRequestService()

    # --- Stack operations ---

    async def create_stack(
        self,
        project_id: UUID,
        name: str,
        *,
        trunk: str = "main",
        base_branch_id: UUID | None = None,
    ) -> Stack:
        """Create a new stack."""
        stack = await self.stack_service.create(
            self.db,
            StackCreate(
                project_id=project_id,
                name=name,
                trunk=trunk,
                base_branch_id=base_branch_id,
            ),
        )
        return stack

    async def get_stack(self, stack_id: UUID) -> Stack:
        """Get a stack by ID or raise."""
        stack = await self.stack_service.get(self.db, stack_id)
        if stack is None or stack.is_deleted:
            raise StackNotFoundError(stack_id)
        return stack

    async def get_stack_with_branches(self, stack_id: UUID) -> dict[str, Any]:
        """Get a stack with all its branches and their pull requests."""
        stack = await self.get_stack(stack_id)
        branches = await self.branch_service.list_by_stack(self.db, stack_id)

        branch_data = []
        for branch in branches:
            pr = await self.pr_service.get_by_branch(self.db, branch.id)
            branch_data.append({"branch": branch, "pull_request": pr})

        return {"stack": stack, "branches": branch_data}

    async def list_stacks_by_project(self, project_id: UUID) -> list[Stack]:
        """List all stacks for a project."""
        return await self.stack_service.list_by_project(self.db, project_id)

    async def delete_stack(self, stack_id: UUID) -> None:
        """Soft-delete a stack."""
        stack = await self.get_stack(stack_id)
        stack.soft_delete()
        await self.db.flush()

    # --- Branch operations ---

    async def add_branch(
        self,
        stack_id: UUID,
        workspace_id: UUID,
        name: str,
        *,
        position: int | None = None,
        head_sha: str | None = None,
    ) -> Branch:
        """Add a branch to a stack.

        If position is None, appends to the end of the stack.
        """
        await self.get_stack(stack_id)  # Validate stack exists

        if position is None:
            max_pos = await self.branch_service.get_max_position(self.db, stack_id)
            position = max_pos + 1

        branch = await self.branch_service.create(
            self.db,
            BranchCreate(
                stack_id=stack_id,
                workspace_id=workspace_id,
                name=name,
                position=position,
                head_sha=head_sha,
            ),
        )
        return branch

    async def get_branch(self, branch_id: UUID) -> Branch:
        """Get a branch by ID or raise."""
        branch = await self.branch_service.get(self.db, branch_id)
        if branch is None or branch.is_deleted:
            raise BranchNotFoundError(branch_id)
        return branch

    async def update_branch_sha(self, branch_id: UUID, head_sha: str) -> Branch:
        """Update a branch's head SHA."""
        branch = await self.get_branch(branch_id)
        updated = await self.branch_service.update(
            self.db, branch.id, BranchUpdate(head_sha=head_sha)
        )
        return updated

    # --- PullRequest operations ---

    async def create_pull_request(
        self,
        branch_id: UUID,
        title: str,
        *,
        description: str | None = None,
        review_notes: str | None = None,
    ) -> PullRequest:
        """Create a pull request for a branch."""
        await self.get_branch(branch_id)  # Validate branch exists

        pr = await self.pr_service.create(
            self.db,
            PullRequestCreate(
                branch_id=branch_id,
                title=title,
                description=description,
                review_notes=review_notes,
            ),
        )
        return pr

    async def get_pull_request(self, pull_request_id: UUID) -> PullRequest:
        """Get a pull request by ID or raise."""
        pr = await self.pr_service.get(self.db, pull_request_id)
        if pr is None or pr.is_deleted:
            raise PullRequestNotFoundError(pull_request_id)
        return pr

    async def link_external_pr(
        self, pull_request_id: UUID, external_id: int, external_url: str
    ) -> PullRequest:
        """Link a pull request to a GitHub PR after submission."""
        pr = await self.get_pull_request(pull_request_id)
        updated = await self.pr_service.update(
            self.db,
            pr.id,
            PullRequestUpdate(external_id=external_id, external_url=external_url),
        )
        return updated

    # --- DAG validation ---

    async def validate_dag(self, stack_id: UUID, base_branch_id: UUID) -> None:
        """Validate that setting base_branch_id does not create a cycle.

        Walks the DAG from base_branch_id upward, checking that we never
        reach a branch belonging to stack_id.
        """
        visited: set[UUID] = set()
        current_branch_id: UUID | None = base_branch_id

        while current_branch_id is not None:
            if current_branch_id in visited:
                raise StackCycleError(stack_id, base_branch_id)
            visited.add(current_branch_id)

            branch = await self.branch_service.get(self.db, current_branch_id)
            if branch is None:
                break

            if branch.stack_id == stack_id:
                raise StackCycleError(stack_id, base_branch_id)

            # Walk up to the parent stack's base_branch_id
            parent_stack = await self.stack_service.get(self.db, branch.stack_id)
            if parent_stack is None:
                break
            current_branch_id = parent_stack.base_branch_id
```

### API Facade: `app/backend/src/molecules/apis/stack_api.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.stacks.schemas.output import StackResponse
from molecules.entities.stack_entity import StackEntity

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class StackDetailResponse:
    """Not a Pydantic model -- a simple container for stack + branch + PR data.

    Serialization happens at the router level using the individual response schemas.
    """

    pass


class StackAPI:
    """API facade for stack domain.

    Coordinates StackEntity and handles serialization. Both REST and CLI
    consume this. Permissions will be added here when auth is implemented.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.entity = StackEntity(db)

    async def create_stack(
        self,
        project_id: UUID,
        name: str,
        *,
        trunk: str = "main",
        base_branch_id: UUID | None = None,
    ) -> StackResponse:
        """Create a new stack."""
        if base_branch_id is not None:
            # Validate DAG before creating -- use a temporary stack_id
            # For new stacks, there can't be a cycle since the stack doesn't exist yet
            pass
        stack = await self.entity.create_stack(
            project_id, name, trunk=trunk, base_branch_id=base_branch_id
        )
        await self.db.commit()
        return StackResponse.model_validate(stack)

    async def get_stack(self, stack_id: UUID) -> StackResponse:
        """Get a stack."""
        stack = await self.entity.get_stack(stack_id)
        return StackResponse.model_validate(stack)

    async def get_stack_detail(self, stack_id: UUID) -> dict:
        """Get a stack with all branches and PRs."""
        data = await self.entity.get_stack_with_branches(stack_id)
        stack = data["stack"]
        branches = []
        for bd in data["branches"]:
            branch_resp = BranchResponse.model_validate(bd["branch"])
            pr_resp = (
                PullRequestResponse.model_validate(bd["pull_request"])
                if bd["pull_request"]
                else None
            )
            branches.append(
                {
                    "branch": branch_resp.model_dump(),
                    "pull_request": pr_resp.model_dump() if pr_resp else None,
                }
            )
        return {
            "stack": StackResponse.model_validate(stack).model_dump(),
            "branches": branches,
        }

    async def list_stacks(self, project_id: UUID) -> list[StackResponse]:
        """List all stacks for a project."""
        stacks = await self.entity.list_stacks_by_project(project_id)
        return [StackResponse.model_validate(s) for s in stacks]

    async def delete_stack(self, stack_id: UUID) -> None:
        """Soft-delete a stack."""
        await self.entity.delete_stack(stack_id)
        await self.db.commit()

    async def add_branch(
        self,
        stack_id: UUID,
        workspace_id: UUID,
        name: str,
        *,
        position: int | None = None,
        head_sha: str | None = None,
    ) -> BranchResponse:
        """Add a branch to a stack."""
        branch = await self.entity.add_branch(
            stack_id, workspace_id, name, position=position, head_sha=head_sha
        )
        await self.db.commit()
        return BranchResponse.model_validate(branch)

    async def create_pull_request(
        self,
        branch_id: UUID,
        title: str,
        *,
        description: str | None = None,
        review_notes: str | None = None,
    ) -> PullRequestResponse:
        """Create a pull request for a branch."""
        pr = await self.entity.create_pull_request(
            branch_id, title, description=description, review_notes=review_notes
        )
        await self.db.commit()
        return PullRequestResponse.model_validate(pr)

    async def link_external_pr(
        self, pull_request_id: UUID, external_id: int, external_url: str
    ) -> PullRequestResponse:
        """Link a PR to a GitHub PR after submission."""
        pr = await self.entity.link_external_pr(
            pull_request_id, external_id, external_url
        )
        await self.db.commit()
        return PullRequestResponse.model_validate(pr)
```

### Tests: `app/backend/__tests__/molecules/test_stack_entity.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stack_entity_init** -- Verify entity composes correct services: `stack_service`, `branch_service`, `pr_service`. Use `AsyncMock()` for db.
2. **test_stack_entity_services_are_correct_types** -- Verify `isinstance` checks for `StackService`, `BranchService`, `PullRequestService`.
3. **test_get_stack_filters_soft_deleted** -- Mock a soft-deleted stack (`.is_deleted = True`), verify `StackNotFoundError` is raised.
4. **test_get_branch_filters_soft_deleted** -- Mock a soft-deleted branch, verify `BranchNotFoundError` is raised.
5. **test_get_pull_request_filters_soft_deleted** -- Mock a soft-deleted PR, verify `PullRequestNotFoundError` is raised.

### Tests: `app/backend/__tests__/molecules/test_stack_api.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stack_api_init** -- Verify `StackAPI` composes `StackEntity`. Use `AsyncMock()` for db.
2. **test_stack_api_has_entity** -- `assert isinstance(api.entity, StackEntity)`.

---

## Phase 5: StackProvider Protocol + StackCLIAdapter (SB-018)

### Files to Create

```
app/backend/src/molecules/providers/__init__.py
app/backend/src/molecules/providers/stack_provider.py
app/backend/src/molecules/providers/stack_cli_adapter.py
app/backend/__tests__/molecules/test_stack_provider.py
app/backend/__tests__/molecules/test_stack_cli_adapter.py
```

### Protocol: `app/backend/src/molecules/providers/stack_provider.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StackResult:
    """Result of a stack CLI operation."""

    success: bool
    output: str
    error: str | None = None


@dataclass
class BranchInfo:
    """Information about a branch from the CLI."""

    name: str
    position: int
    head_sha: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None


@dataclass
class StackInfo:
    """Information about a stack from the CLI."""

    name: str
    trunk: str
    branches: list[BranchInfo]


class StackProvider(Protocol):
    """Contract for git stacking operations.

    Implementations wrap a stacking tool (CLI binary or native git+GitHub API)
    to perform git operations and report results back to the domain layer.
    """

    async def create_stack(
        self, name: str, *, trunk: str = "main"
    ) -> StackResult:
        """Create a new stack in the git tool."""
        ...

    async def get_status(self, stack_name: str) -> StackInfo:
        """Get current status of a stack from the git tool."""
        ...

    async def push(
        self, stack_name: str, *, branch_positions: list[int] | None = None
    ) -> StackResult:
        """Push branches to remote. If branch_positions is None, push all."""
        ...

    async def submit(self, stack_name: str) -> StackResult:
        """Submit stack -- create/update GitHub PRs."""
        ...

    async def restack(self, stack_name: str) -> StackResult:
        """Rebase downstream branches after mid-stack edits."""
        ...

    async def sync(self, stack_name: str) -> StackResult:
        """Sync stack -- clean up after PRs merge."""
        ...
```

### Adapter: `app/backend/src/molecules/providers/stack_cli_adapter.py`

```python
from __future__ import annotations

import asyncio
import shutil

from molecules.providers.stack_provider import BranchInfo, StackInfo, StackResult


class StackCLIAdapter:
    """Wraps the existing `stack` CLI binary (dugshub/stack).

    Installed globally via Bun at ~/.bun/bin/stack. Executes CLI commands
    as async subprocesses and parses output.

    This is a short-term adapter. The long-term plan (NativeStackAdapter)
    will use direct git + GitHub API calls.
    """

    def __init__(self, binary_path: str | None = None) -> None:
        self.binary_path = binary_path or self._find_binary()

    @staticmethod
    def _find_binary() -> str:
        """Find the stack binary on PATH or at known locations."""
        # Check PATH first
        found = shutil.which("stack")
        if found:
            return found
        # Known Bun global install location
        import os
        bun_path = os.path.expanduser("~/.bun/bin/stack")
        if os.path.isfile(bun_path):
            return bun_path
        raise FileNotFoundError(
            "stack CLI binary not found. Install via: bun install -g @pattern-stack/stack"
        )

    async def _run(self, *args: str) -> tuple[str, str, int]:
        """Run a stack CLI command and return (stdout, stderr, returncode)."""
        proc = await asyncio.create_subprocess_exec(
            self.binary_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            proc.returncode or 0,
        )

    async def create_stack(
        self, name: str, *, trunk: str = "main"
    ) -> StackResult:
        """Create a new stack via CLI."""
        stdout, stderr, code = await self._run("create", name)
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def get_status(self, stack_name: str) -> StackInfo:
        """Get stack status via CLI.

        Parses the output of `stack status` to extract branch info.
        """
        # Switch to the stack first
        await self._run(stack_name)
        stdout, stderr, code = await self._run("status")

        # Parse output -- this is fragile and will be replaced
        # by the NativeStackAdapter. For now, return minimal info.
        branches: list[BranchInfo] = []
        return StackInfo(name=stack_name, trunk="main", branches=branches)

    async def push(
        self, stack_name: str, *, branch_positions: list[int] | None = None
    ) -> StackResult:
        """Push via CLI. Maps to `stack submit` (which pushes + creates PRs)."""
        args = ["submit"]
        if branch_positions:
            args.extend(str(p) for p in branch_positions)
        stdout, stderr, code = await self._run(*args)
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def submit(self, stack_name: str) -> StackResult:
        """Submit via CLI. Maps to `stack submit`."""
        stdout, stderr, code = await self._run("submit")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def restack(self, stack_name: str) -> StackResult:
        """Restack via CLI. Maps to `stack restack`."""
        stdout, stderr, code = await self._run("restack")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )

    async def sync(self, stack_name: str) -> StackResult:
        """Sync via CLI. Maps to `stack sync`."""
        stdout, stderr, code = await self._run("sync")
        return StackResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )
```

### Exports: `app/backend/src/molecules/providers/__init__.py`

```python
from .stack_cli_adapter import StackCLIAdapter
from .stack_provider import BranchInfo, StackInfo, StackProvider, StackResult

__all__ = [
    "StackProvider",
    "StackResult",
    "BranchInfo",
    "StackInfo",
    "StackCLIAdapter",
]
```

### Tests: `app/backend/__tests__/molecules/test_stack_provider.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stack_result_dataclass** -- Create `StackResult(success=True, output="ok")`, verify fields. Verify `error` defaults to `None`.
2. **test_stack_result_with_error** -- Create `StackResult(success=False, output="", error="failed")`, verify error field.
3. **test_branch_info_dataclass** -- Create `BranchInfo(name="user/stack/1-feat", position=1)`, verify `head_sha` and `pr_number` default to `None`.
4. **test_branch_info_full** -- Create with all fields including `head_sha`, `pr_number`, `pr_url`.
5. **test_stack_info_dataclass** -- Create `StackInfo(name="my-stack", trunk="main", branches=[])`, verify fields.
6. **test_stack_provider_is_protocol** -- Verify `StackProvider` is a `Protocol` subclass (check `typing.runtime_checkable` is not needed -- just verify structure). Import and verify it has the expected methods: `create_stack`, `get_status`, `push`, `submit`, `restack`, `sync`.

### Tests: `app/backend/__tests__/molecules/test_stack_cli_adapter.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stack_cli_adapter_init_with_path** -- `StackCLIAdapter(binary_path="/usr/bin/stack")`, verify `binary_path` is set.
2. **test_stack_cli_adapter_find_binary_not_found** -- Mock `shutil.which` to return `None` and `os.path.isfile` to return `False`. Verify `FileNotFoundError` is raised.
3. **test_stack_cli_adapter_has_provider_methods** -- Verify `StackCLIAdapter` has all methods defined in `StackProvider`: `create_stack`, `get_status`, `push`, `submit`, `restack`, `sync`.
4. **test_stack_cli_adapter_run** -- Mock `asyncio.create_subprocess_exec` to return a mock process. Call `_run("status")`, verify the binary path and args are passed correctly.
5. **test_stack_cli_adapter_create_stack** -- Mock `_run` to return `("Created stack", "", 0)`. Call `create_stack("my-stack")`, verify returns `StackResult(success=True, ...)`.
6. **test_stack_cli_adapter_create_stack_failure** -- Mock `_run` to return `("", "error msg", 1)`. Verify returns `StackResult(success=False, error="error msg")`.

---

## Phase 6: REST API Routers (SB-019)

### Files to Create

```
app/backend/src/organisms/api/routers/stacks.py
app/backend/__tests__/organisms/test_stack_routers.py
```

### Files to Modify

```
app/backend/src/organisms/api/dependencies.py   -- add StackAPI dependency
app/backend/src/organisms/api/app.py             -- register stacks router
app/backend/__tests__/organisms/test_routers.py  -- add route registration test
```

### Router: `app/backend/src/organisms/api/routers/stacks.py`

```python
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from features.branches.schemas.output import BranchResponse
from features.pull_requests.schemas.output import PullRequestResponse
from features.stacks.schemas.output import StackResponse
from organisms.api.dependencies import StackAPIDep

router = APIRouter(prefix="/stacks", tags=["stacks"])


# --- Request schemas (router-local, like CreateConversationRequest) ---


class CreateStackRequest(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    trunk: str = Field("main", min_length=1, max_length=200)
    base_branch_id: UUID | None = None


class AddBranchRequest(BaseModel):
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=500)
    position: int | None = Field(None, ge=1)
    head_sha: str | None = Field(None, max_length=40)


class CreatePullRequestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    review_notes: str | None = None


class LinkExternalPRRequest(BaseModel):
    external_id: int
    external_url: str = Field(..., max_length=500)


# --- Stack endpoints ---


@router.post("/", response_model=StackResponse, status_code=201)
async def create_stack(
    data: CreateStackRequest, api: StackAPIDep
) -> StackResponse:
    return await api.create_stack(
        data.project_id,
        data.name,
        trunk=data.trunk,
        base_branch_id=data.base_branch_id,
    )


@router.get("/", response_model=list[StackResponse])
async def list_stacks(
    api: StackAPIDep,
    project_id: UUID = Query(...),
) -> list[StackResponse]:
    return await api.list_stacks(project_id)


@router.get("/{stack_id}", response_model=StackResponse)
async def get_stack(stack_id: UUID, api: StackAPIDep) -> StackResponse:
    return await api.get_stack(stack_id)


@router.get("/{stack_id}/detail")
async def get_stack_detail(stack_id: UUID, api: StackAPIDep) -> dict:
    """Get stack with all branches and pull requests."""
    return await api.get_stack_detail(stack_id)


@router.delete("/{stack_id}", status_code=204)
async def delete_stack(stack_id: UUID, api: StackAPIDep) -> None:
    await api.delete_stack(stack_id)


# --- Branch endpoints (nested under stack) ---


@router.post(
    "/{stack_id}/branches", response_model=BranchResponse, status_code=201
)
async def add_branch(
    stack_id: UUID, data: AddBranchRequest, api: StackAPIDep
) -> BranchResponse:
    return await api.add_branch(
        stack_id,
        data.workspace_id,
        data.name,
        position=data.position,
        head_sha=data.head_sha,
    )


# --- PullRequest endpoints (nested under branch) ---


@router.post(
    "/{stack_id}/branches/{branch_id}/pr",
    response_model=PullRequestResponse,
    status_code=201,
)
async def create_pull_request(
    stack_id: UUID,
    branch_id: UUID,
    data: CreatePullRequestRequest,
    api: StackAPIDep,
) -> PullRequestResponse:
    return await api.create_pull_request(
        branch_id,
        data.title,
        description=data.description,
        review_notes=data.review_notes,
    )


@router.post(
    "/pull-requests/{pull_request_id}/link",
    response_model=PullRequestResponse,
)
async def link_external_pr(
    pull_request_id: UUID,
    data: LinkExternalPRRequest,
    api: StackAPIDep,
) -> PullRequestResponse:
    return await api.link_external_pr(
        pull_request_id, data.external_id, data.external_url
    )
```

### Dependencies: `app/backend/src/organisms/api/dependencies.py`

Add after existing dependencies:

```python
from molecules.apis.stack_api import StackAPI


def get_stack_api(db: DatabaseSession) -> StackAPI:
    return StackAPI(db)


StackAPIDep = Annotated[StackAPI, Depends(get_stack_api)]
```

### App Registration: `app/backend/src/organisms/api/app.py`

Add import and registration:

```python
from organisms.api.routers.stacks import router as stacks_router

# In create_app(), after existing router registrations:
app.include_router(stacks_router, prefix="/api/v1")
```

### Tests: `app/backend/__tests__/organisms/test_stack_routers.py`

Test cases (all `@pytest.mark.unit`):

1. **test_stacks_router_registered** -- Verify `/stacks` routes exist in `app.routes`.
2. **test_stacks_branches_router_registered** -- Verify `/stacks/{stack_id}/branches` routes exist.
3. **test_stacks_pr_router_registered** -- Verify `/stacks/{stack_id}/branches/{branch_id}/pr` routes exist.

### Modify: `app/backend/__tests__/organisms/test_routers.py`

Add:

4. **test_stacks_router_registered** -- Same pattern as existing `test_conversations_router_registered`: check `any("/stacks" in r for r in routes)`.

---

## Phase 7: Alembic Migration + Seed Data (SB-020)

### Files to Create

```
app/backend/alembic/versions/<auto>_add_stacks_branches_pull_requests.py
```

### Files to Modify

```
app/backend/src/features/__init__.py  -- add model imports for alembic discovery
```

### Migration Generation

Generate via: `cd app/backend && just migrate-gen "add stacks branches pull requests"`

The migration must handle a circular FK dependency: `stacks.base_branch_id -> branches.id` and `branches.stack_id -> stacks.id`. The solution is a two-phase approach:

1. Create `stacks` table WITHOUT the `base_branch_id` FK constraint
2. Create `branches` table with `stack_id` FK -> `stacks.id`
3. Create `pull_requests` table with `branch_id` FK -> `branches.id`
4. Add `base_branch_id` FK constraint to `stacks` via `ALTER TABLE`
5. Add `worktrees.branch_id` FK constraint via `ALTER TABLE` (the column already exists from EP-005 SB-034, but the FK was deferred until `branches` table exists)

### Migration Tables

**Table: `stacks`** (created first, base_branch_id FK added after branches)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| project_id | UUID | NOT NULL, FK -> projects.id |
| name | String(200) | NOT NULL |
| base_branch_id | UUID | nullable (FK added in step 4) |
| trunk | String(200) | NOT NULL |
| state | String(50) | NOT NULL |
| deleted_at | DateTime(tz) | nullable |
| reference_number | String(50) | nullable |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

Indexes:
- `ix_stacks_project_id` on `project_id`
- `ix_stacks_name` on `name`
- `ix_stacks_base_branch_id` on `base_branch_id`
- `ix_stacks_state` on `state`
- `ix_stacks_reference_number` on `reference_number`, unique

**Table: `branches`**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| stack_id | UUID | NOT NULL, FK -> stacks.id |
| workspace_id | UUID | NOT NULL, FK -> workspaces.id |
| name | String(500) | NOT NULL |
| position | Integer | NOT NULL |
| head_sha | String(40) | nullable |
| state | String(50) | NOT NULL |
| deleted_at | DateTime(tz) | nullable |
| reference_number | String(50) | nullable |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

Constraints:
- `uq_branch_stack_position` UNIQUE on (`stack_id`, `position`)

Indexes:
- `ix_branches_stack_id` on `stack_id`
- `ix_branches_workspace_id` on `workspace_id`
- `ix_branches_state` on `state`
- `ix_branches_reference_number` on `reference_number`, unique

**Table: `pull_requests`**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, server_default gen_random_uuid() |
| branch_id | UUID | NOT NULL, FK -> branches.id, UNIQUE |
| external_id | Integer | nullable |
| external_url | String(500) | nullable |
| title | String(500) | NOT NULL |
| description | Text | nullable |
| review_notes | Text | nullable |
| state | String(50) | NOT NULL |
| deleted_at | DateTime(tz) | nullable |
| reference_number | String(50) | nullable |
| created_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |
| updated_at | DateTime(tz) | NOT NULL, server_default CURRENT_TIMESTAMP |

Indexes:
- `ix_pull_requests_branch_id` on `branch_id`, unique
- `ix_pull_requests_state` on `state`
- `ix_pull_requests_reference_number` on `reference_number`, unique

**Step 4: Add stacks.base_branch_id FK constraint**

```python
op.create_foreign_key(
    "fk_stacks_base_branch_id",
    "stacks",
    "branches",
    ["base_branch_id"],
    ["id"],
)
```

**Step 5: Add worktrees.branch_id FK constraint**

The `worktrees` table and `branch_id` column already exist (created by EP-005 SB-034). This migration adds only the FK constraint that was deferred because the `branches` table did not exist yet.

```python
op.create_foreign_key(
    "fk_worktrees_branch_id",
    "worktrees",
    "branches",
    ["branch_id"],
    ["id"],
)
```

### Model Registry: `app/backend/src/features/__init__.py`

Add imports:

```python
from features.stacks.models import Stack  # noqa: F401
from features.branches.models import Branch  # noqa: F401
from features.pull_requests.models import PullRequest  # noqa: F401
```

### Downgrade

The downgrade must:

1. Drop FK `fk_worktrees_branch_id` from `worktrees` (leave the column -- it belongs to EP-005)
2. Drop FK `fk_stacks_base_branch_id` from `stacks`
3. Drop `pull_requests` table (FK dependency on `branches`)
4. Drop `branches` table (FK dependency on `stacks`)
5. Drop `stacks` table

### Seed Data

No seed data for stacks, branches, or pull requests. These are user-created entities, not reference data. The existing seed system (`app/backend/src/seeds/`) is for agent definitions and role templates -- static configuration, not user data.

---

## Complete File Tree

### New Files

```
app/backend/src/features/stacks/__init__.py                     # Exports: Stack, StackCreate, StackUpdate, StackResponse, StackService
app/backend/src/features/stacks/models.py                        # EventPattern model with state machine
app/backend/src/features/stacks/schemas/__init__.py              # Empty
app/backend/src/features/stacks/schemas/input.py                 # StackCreate, StackUpdate
app/backend/src/features/stacks/schemas/output.py                # StackResponse
app/backend/src/features/stacks/service.py                       # StackService with list_by_project(), get_by_name(), get_dependents()

app/backend/src/features/branches/__init__.py                    # Exports: Branch, BranchCreate, BranchUpdate, BranchResponse, BranchService
app/backend/src/features/branches/models.py                      # EventPattern model with UniqueConstraint + state machine
app/backend/src/features/branches/schemas/__init__.py            # Empty
app/backend/src/features/branches/schemas/input.py               # BranchCreate, BranchUpdate
app/backend/src/features/branches/schemas/output.py              # BranchResponse
app/backend/src/features/branches/service.py                     # BranchService with list_by_stack(), get_by_name(), get_max_position(), list_by_workspace()

app/backend/src/features/pull_requests/__init__.py               # Exports: PullRequest, PullRequestCreate, PullRequestUpdate, PullRequestResponse, PullRequestService
app/backend/src/features/pull_requests/models.py                 # EventPattern model with unique branch_id
app/backend/src/features/pull_requests/schemas/__init__.py       # Empty
app/backend/src/features/pull_requests/schemas/input.py          # PullRequestCreate, PullRequestUpdate
app/backend/src/features/pull_requests/schemas/output.py         # PullRequestResponse
app/backend/src/features/pull_requests/service.py                # PullRequestService with get_by_branch(), get_by_external_id()

app/backend/src/molecules/entities/stack_entity.py               # Domain aggregate: Stack + Branch + PullRequest lifecycle
app/backend/src/molecules/apis/stack_api.py                      # API facade with serialization
app/backend/src/molecules/providers/__init__.py                  # Exports: StackProvider, StackResult, StackCLIAdapter, etc.
app/backend/src/molecules/providers/stack_provider.py            # Protocol + dataclasses (StackResult, BranchInfo, StackInfo)
app/backend/src/molecules/providers/stack_cli_adapter.py         # CLI binary wrapper

app/backend/src/organisms/api/routers/stacks.py                 # REST router: stacks + branches + PRs
app/backend/alembic/versions/<auto>_add_stacks_branches_pull_requests.py  # Migration

app/backend/__tests__/features/test_stacks.py                   # 14 unit tests
app/backend/__tests__/features/test_branches.py                  # 13 unit tests
app/backend/__tests__/features/test_pull_requests.py             # 16 unit tests
app/backend/__tests__/molecules/test_stack_entity.py             # 5 unit tests
app/backend/__tests__/molecules/test_stack_api.py                # 2 unit tests
app/backend/__tests__/molecules/test_stack_provider.py           # 6 unit tests
app/backend/__tests__/molecules/test_stack_cli_adapter.py        # 6 unit tests
app/backend/__tests__/organisms/test_stack_routers.py            # 3 unit tests
```

### Modified Files

```
app/backend/src/features/__init__.py                             # Add Stack, Branch, PullRequest model imports
app/backend/src/molecules/exceptions.py                          # Add StackNotFoundError, BranchNotFoundError, PullRequestNotFoundError, StackCycleError
app/backend/src/organisms/api/dependencies.py                    # Add StackAPI dependency
app/backend/src/organisms/api/app.py                             # Register stacks_router
app/backend/__tests__/organisms/test_routers.py                  # Add stacks route registration test
```

---

## Key Design Decisions

1. **All three entities use EventPattern** -- Stack, Branch, and PullRequest all have genuine state machines with lifecycle semantics. The states model the three-tier workflow: local (created) -> private workspace (pushed/reviewing/ready) -> GitHub (submitted/merged).

2. **Circular FK handled via migration phasing** -- `stacks.base_branch_id -> branches.id` and `branches.stack_id -> stacks.id` create a circular reference. The model declares both FKs, but the migration creates the `base_branch_id` FK as a deferred `ALTER TABLE` after both tables exist. SQLAlchemy handles this at the ORM level without issue; only the DDL needs ordering.

3. **PullRequest uses column-level unique on branch_id** -- `Field(UUID, ..., unique=True)` enforces the 1:1 constraint. No need for a separate `UniqueConstraint` in `__table_args__` since it's a single column.

4. **Branch.position uses UniqueConstraint** -- `UniqueConstraint("stack_id", "position")` prevents two branches from occupying the same position in a stack. This follows the `Message.UniqueConstraint("conversation_id", "sequence")` pattern already in the codebase.

5. **StackProvider is a Protocol, not ABC** -- Follows the existing pattern in the codebase (e.g., `RunnerProtocol` in agentic-patterns). Protocols enable structural typing without inheritance coupling.

6. **StackCLIAdapter wraps `/Users/dug/.bun/bin/stack`** -- The stack CLI is installed globally via Bun. The adapter uses `asyncio.create_subprocess_exec` for non-blocking CLI calls. The `_find_binary()` method checks `PATH` first, then the known Bun install location.

7. **Router nests branches under stacks, PRs under branches** -- URL hierarchy: `POST /stacks/{id}/branches`, `POST /stacks/{id}/branches/{id}/pr`. This reflects ownership. The `link_external_pr` endpoint is flat (`POST /pull-requests/{id}/link`) since it doesn't need stack context.

8. **No molecule for Project+Stack coordination yet** -- The StackEntity composes Stack+Branch+PR. Project is accessed via the FK. If cross-domain coordination is needed later (e.g., project-level stack operations), a ProjectEntity can emerge.

9. **DAG validation in StackEntity** -- The `validate_dag()` method walks the chain of `base_branch_id -> stack -> base_branch_id` to detect cycles. This is O(n) where n is the depth of the stack DAG, which is always small in practice.

10. **No seed data** -- Stacks, branches, and PRs are user-created runtime entities, not reference data like agent definitions.

---

## Testing Strategy

### Unit Tests (no DB required)

All tests use `@pytest.mark.unit`. The patterns follow existing conventions:
- Model field existence via `hasattr()`
- Pattern config via `Model.Pattern.xxx` assertions
- State machine via `transition_to()` and `can_transition_to()` on in-memory instances
- Schema validation via Pydantic construction and `ValidationError`
- Service model binding via `Service().model is Model`
- Entity/API composition via `isinstance()` checks with `AsyncMock` db
- Router registration via `app.routes` inspection
- CLI adapter via mocked subprocess calls

### Test Counts

| Test File | Count | Focus |
|-----------|-------|-------|
| test_stacks.py | 14 | Model, Pattern, state machine (7 paths), schemas, service |
| test_branches.py | 13 | Model, Pattern, state machine, UniqueConstraint, schemas, service |
| test_pull_requests.py | 16 | Model, Pattern, state machine (reopen path), schemas, service |
| test_stack_entity.py | 5 | Entity composition, soft-delete filtering |
| test_stack_api.py | 2 | API facade composition |
| test_stack_provider.py | 6 | Protocol dataclasses, method existence |
| test_stack_cli_adapter.py | 6 | Binary discovery, subprocess mocking |
| test_stack_routers.py | 3 | Route registration |
| test_routers.py (addition) | 1 | Stacks route registration |
| **Total new tests** | **66** | |

---

## Open Questions

None. The domain model is well-defined in EP-003, ADR-004, and the EP-005 spec. All pattern types, field definitions, and layer assignments follow established conventions in the codebase.

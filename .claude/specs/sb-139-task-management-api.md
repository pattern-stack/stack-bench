---
title: TaskManagementAPI facade
date: 2026-03-24
status: implemented
issue: SB-139
branch: worktree-warm-crunching-lantern
depends_on: [SB-137, SB-138]
adrs: []
---

# TaskManagementAPI Facade

## Goal

Provide a unified API facade for REST and CLI consumption of the task management domain. Follows the StackAPI pattern: composes TaskManagementEntity + SyncEngine, handles serialization to response models, and manages db commits.

## Design

**Pattern:** API facade (same as StackAPI)

- Takes `AsyncSession` in `__init__`, creates `TaskManagementEntity` internally
- Optionally accepts a `TaskProvider` adapter; if provided, creates a `SyncEngine`
- Every mutating method calls `await self.db.commit()` after the entity call
- Every method returning data uses `XxxResponse.model_validate(obj)`
- Sync methods raise `SyncNotConfiguredError` if no adapter was provided

## API Surface

- **Tasks:** create, get, list (by project or sprint), update, delete, transition
- **Projects:** create, get, list
- **Sprints:** create, get, get_active, list
- **Comments:** add, list
- **Tags:** apply, remove, get_task_tags
- **Relations:** add, get_task_relations, get_blockers
- **Sync:** sync_tasks (full pull), sync_task (push single)

## Files

- `app/backend/src/molecules/apis/task_management_api.py` -- API facade
- `app/backend/src/molecules/exceptions.py` -- Added `SyncNotConfiguredError`
- `app/backend/__tests__/molecules/test_task_management_api.py` -- Unit tests

---
status: draft
issue: SB-124
date: 2026-03-24
---

# SB-124: TaskProject Model, Service, and Schemas

## Summary

Add the `TaskProject` feature -- an EventPattern model representing PM project/milestone groupings for tasks. This is distinct from the existing `Project` model (which represents git repos).

## State Machine

```
backlog -> planning -> active -> on_hold -> completed -> archived
                        ^          |
                        +----------+  (bidirectional)
```

- `archived` is terminal (no outbound transitions)
- `on_hold` is reversible back to `active`

## Fields

| Field | Type | Notes |
|-------|------|-------|
| name | str | required, max_length=500, indexed |
| description | str | nullable |
| lead_id | UUID | nullable, no FK constraint, indexed |
| external_id | str | nullable, max_length=200, indexed |
| external_url | str | nullable, max_length=500 |
| provider | str | default="local", choices: github/linear/local |
| last_synced_at | datetime | nullable |

## Pattern Config

- entity: `task_project`
- reference_prefix: `TPJ`
- emit_state_transitions: True
- track_changes: True

## Files

- `app/backend/src/features/task_projects/models.py`
- `app/backend/src/features/task_projects/service.py`
- `app/backend/src/features/task_projects/schemas/input.py`
- `app/backend/src/features/task_projects/schemas/output.py`
- `app/backend/src/features/task_projects/schemas/__init__.py`
- `app/backend/src/features/task_projects/__init__.py`
- `app/backend/__tests__/features/test_task_projects.py`

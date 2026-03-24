---
status: draft
issue: SB-125
date: 2026-03-24
---

# SB-125: Sprint Model, Service, and Schemas

## Summary

Add a Sprint feature to the features layer following the EventPattern with states `planned -> active -> completed`. Sprints belong to a project and support external sync (GitHub milestones, Linear cycles).

## Model

- **Pattern**: EventPattern
- **Table**: `sprints`
- **Entity**: `sprint`, reference prefix `SPR`
- **States**: `planned` (initial) -> `active` -> `completed` (terminal)
- **Domain fields**: name (str, required), number (int, nullable), description (nullable), starts_at (datetime, nullable), ends_at (datetime, nullable)
- **Foreign keys**: project_id -> task_projects.id (nullable)
- **External sync**: external_id, external_url, provider (github/linear/local), last_synced_at
- **Config**: emit_state_transitions=True, track_changes=True

## Schemas

- **SprintCreate**: name required, all others optional with defaults
- **SprintUpdate**: all fields optional for partial updates
- **SprintResponse**: full model output with from_attributes=True

## Service

- **SprintService(BaseService[Sprint, SprintCreate, SprintUpdate])**
- `get_active_sprint(db, project_id)` — returns the active sprint for a project (or None)
- `list_by_project(db, project_id)` — returns all sprints for a project

## Files

- `app/backend/src/features/sprints/__init__.py`
- `app/backend/src/features/sprints/models.py`
- `app/backend/src/features/sprints/service.py`
- `app/backend/src/features/sprints/schemas/__init__.py`
- `app/backend/src/features/sprints/schemas/input.py`
- `app/backend/src/features/sprints/schemas/output.py`
- `app/backend/__tests__/features/test_sprints.py`

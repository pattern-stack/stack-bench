---
title: Alembic migrations for all task management models
date: 2026-03-24
status: draft
issue: SB-129
branch: worktree-warm-crunching-lantern
depends_on: [SB-123, SB-124, SB-125, SB-126, SB-127, SB-128]
adrs: []
---

# Alembic Migrations for Task Management Models

## Goal

Create a single Alembic migration covering all seven task management tables, ensuring proper dependency order and full index coverage.

## Tables

1. **task_projects** (EventPattern) -- no new-table FKs
2. **sprints** (EventPattern) -- FK to task_projects
3. **tasks** (EventPattern) -- FKs to task_projects, sprints
4. **task_comments** (BasePattern) -- FK to tasks, self-ref parent_id
5. **task_tags** (BasePattern) -- unique on name
6. **task_tag_assignments** -- junction table, composite PK (task_id, tag_id)
7. **task_relations** (BasePattern) -- FKs to tasks, unique constraint on (source_task_id, target_task_id, relation_type)

## Indexes

- task_projects: name, lead_id, external_id, state, reference_number (unique)
- sprints: name, number, project_id, external_id, starts_at, state, reference_number (unique)
- tasks: title, project_id, assignee_id, sprint_id, external_id, state, reference_number (unique)
- task_comments: task_id, author_id, parent_id, external_id
- task_tags: name (unique), external_id
- task_relations: source_task_id, target_task_id, external_id

## Implementation

- Migration file: `alembic/versions/a3f7c8d91e42_add_task_management_tables.py`
- Model imports added to `features/__init__.py` for alembic discovery
- Down revision: `1505160361ec` (latest existing migration)
- Downgrade drops tables in reverse dependency order

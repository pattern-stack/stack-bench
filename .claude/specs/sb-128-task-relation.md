---
status: draft
issue: SB-128
date: 2026-03-24
---

# SB-128: TaskRelation Model, Service, and Schemas

## Overview

Add a TaskRelation feature to model relationships between tasks: parent/child, blocking, relates-to, and duplicate links.

## Model

- **Pattern**: BasePattern (no state machine)
- **Table**: `task_relations`
- **Entity**: `task_relation`, prefix `TRL`
- **Fields**: source_task_id (FK tasks.id), target_task_id (FK tasks.id), relation_type (enum: parent_of, blocks, relates_to, duplicates)
- **Unique constraint**: (source_task_id, target_task_id, relation_type)
- **External sync**: external_id, external_url, provider (github/linear/local), last_synced_at

## Service

- BaseService[TaskRelation, TaskRelationCreate, TaskRelationUpdate]
- `get_task_relations(db, task_id)` — all relations where task is source OR target
- `get_blockers(db, task_id)` — relations where target=task_id, type=blocks
- `get_children(db, task_id)` — relations where source=task_id, type=parent_of
- `get_parent(db, task_id)` — relation where target=task_id, type=parent_of

## Schemas

- TaskRelationCreate: source_task_id, target_task_id, relation_type (required), plus external sync fields
- TaskRelationUpdate: relation_type (optional), plus external sync fields
- TaskRelationResponse: all fields with from_attributes=True

## Files

- `app/backend/src/features/task_relations/__init__.py`
- `app/backend/src/features/task_relations/models.py`
- `app/backend/src/features/task_relations/service.py`
- `app/backend/src/features/task_relations/schemas/__init__.py`
- `app/backend/src/features/task_relations/schemas/input.py`
- `app/backend/src/features/task_relations/schemas/output.py`
- `app/backend/__tests__/features/test_task_relations.py`

---
status: draft
issue: SB-127
date: 2026-03-24
---

# SB-127: TaskTag Model, Service, and Schemas

## Summary

Add a TaskTag feature to the backend using BasePattern (no state machine). Supports tag name, color, description, grouping with exclusivity constraints, and external sync fields. Includes a many-to-many association table (task_tag_assignments) linking tasks to tags.

## Model

- **Pattern**: BasePattern (entity="task_tag", reference_prefix="TTG")
- **Table**: task_tags
- **Fields**:
  - name (str, required, unique, max_length=100)
  - color (str, nullable, max_length=7 for hex)
  - description (str, nullable)
  - group (str, nullable, max_length=100) -- for grouping tags like "priority", "area", "type"
  - is_exclusive (bool, default=False) -- if true, only one tag from this group can be applied
  - external_id, external_url, provider, last_synced_at -- external sync fields

## Association Table

- **Table**: task_tag_assignments (SQLAlchemy Table() construct, not a model class)
- **Columns**: task_id (FK -> tasks.id), tag_id (FK -> task_tags.id)
- **Primary key**: composite (task_id, tag_id)

## Service

- TaskTagService(BaseService[TaskTag, TaskTagCreate, TaskTagUpdate])
- Custom queries: list_by_group(group), get_by_name(name)
- Tag operations: apply_tag, remove_tag, get_task_tags, set_task_tags

## Schemas

- TaskTagCreate: name (required), color, description, group, is_exclusive, sync fields
- TaskTagUpdate: all fields optional
- TaskTagResponse: all fields + id, reference_number, created_at, updated_at

## Files

- `app/backend/src/features/task_tags/__init__.py`
- `app/backend/src/features/task_tags/models.py`
- `app/backend/src/features/task_tags/service.py`
- `app/backend/src/features/task_tags/schemas/__init__.py`
- `app/backend/src/features/task_tags/schemas/input.py`
- `app/backend/src/features/task_tags/schemas/output.py`
- `app/backend/__tests__/features/test_task_tags.py`

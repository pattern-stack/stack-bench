---
status: draft
issue: SB-126
date: 2026-03-24
---

# SB-126: TaskComment Model, Service, and Schemas

## Summary

Add a TaskComment feature to the backend using BasePattern (no state machine). Supports markdown body text, task association, optional threading via parent_id, optional author tracking, and external sync fields for GitHub/Linear/local providers.

## Model

- **Pattern**: BasePattern (entity="task_comment", reference_prefix="TCM")
- **Table**: task_comments
- **Fields**:
  - body (str, required) -- markdown content
  - edited_at (datetime, nullable) -- tracks when comment was edited
  - task_id (UUID, FK -> tasks.id, required)
  - author_id (UUID, nullable, no FK constraint)
  - parent_id (UUID, FK -> task_comments.id, nullable, self-referencing for threading)
  - external_id, external_url, provider, last_synced_at -- external sync fields

## Service

- TaskCommentService(BaseService[TaskComment, TaskCommentCreate, TaskCommentUpdate])
- Custom methods: list_by_task, list_by_author, get_thread

## Schemas

- TaskCommentCreate: body (required), task_id (required), author_id, parent_id, sync fields
- TaskCommentUpdate: body, edited_at, sync fields (all optional)
- TaskCommentResponse: all fields including timestamps, from_attributes=True

## Files

- app/backend/src/features/task_comments/{__init__,models,service}.py
- app/backend/src/features/task_comments/schemas/{__init__,input,output}.py
- app/backend/__tests__/features/test_task_comments.py

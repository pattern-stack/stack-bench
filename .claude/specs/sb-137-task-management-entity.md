---
title: "SB-137: TaskManagementEntity Domain Aggregate"
status: implemented
created: 2026-03-24
issue: SB-137
epic: EP-011
---

# SB-137: TaskManagementEntity Domain Aggregate

## Summary

Domain aggregate that coordinates all 6 task management feature services (tasks, projects, sprints, comments, tags, relations) following the StackEntity pattern.

## Files

- `app/backend/src/molecules/entities/task_management_entity.py` -- Entity implementation
- `app/backend/src/molecules/exceptions.py` -- Added 5 new exception types
- `app/backend/__tests__/molecules/test_task_management_entity.py` -- 26 unit tests

## Operations

### Task lifecycle
- create_task, get_task, update_task, delete_task (with blocker check)
- list_tasks_by_project, list_tasks_by_sprint, transition_task

### Project operations
- create_project, get_project, list_projects

### Sprint operations
- create_sprint, get_sprint, get_active_sprint, list_sprints_by_project

### Comment operations
- add_comment (validates task exists), list_comments

### Tag operations
- apply_tag (with group exclusivity enforcement), remove_tag, get_task_tags

### Relation operations
- add_relation (with cycle detection for parent_of/blocks), get_task_relations, get_blockers

## Business Rules

1. Cannot delete a task with open (non-done/cancelled) blockers -- raises TaskHasBlockersError
2. Tag exclusivity: applying an exclusive tag removes other tags from same group first
3. Cycle detection: walks the relation graph before creating parent_of or blocks relations

## Exceptions Added

- TaskNotFoundError, TaskProjectNotFoundError, SprintNotFoundError
- TaskHasBlockersError, RelationCycleError

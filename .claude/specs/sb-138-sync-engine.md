---
title: "SB-138: SyncEngine for Bi-directional Provider Sync"
status: implemented
created: 2026-03-24
issue: SB-138
epic: EP-011
---

# SB-138: SyncEngine for Bi-directional Provider Sync

## Summary

Sync engine that coordinates between the local DB (via TaskManagementEntity) and external providers (GitHub Issues, Linear) using a TaskProvider protocol. Implements pull (provider to local), push (local to provider), and full sync with last-write-wins conflict resolution.

## Files

- `app/backend/src/molecules/providers/task_provider.py` -- TaskProvider Protocol + DTOs (ExternalTask, ExternalComment, SyncResult)
- `app/backend/src/molecules/services/sync_engine.py` -- SyncEngine implementation
- `app/backend/src/molecules/services/__init__.py` -- Package init
- `app/backend/src/molecules/providers/__init__.py` -- Updated exports
- `app/backend/src/features/tasks/service.py` -- Added get_by_external_id
- `app/backend/src/features/task_comments/service.py` -- Added get_by_external_id
- `app/backend/__tests__/molecules/test_sync_engine.py` -- 19 unit tests

## Protocol

TaskProvider defines 6 async methods: list_tasks, get_task, create_task, update_task, list_comments, create_comment. External adapters (GitHub, Linear) implement this protocol.

## Operations

- **pull_tasks** -- Fetch from provider, upsert locally by external_id
- **push_task** -- Push local task to provider, store returned external_id
- **pull_comments** -- Fetch comments for a task from provider
- **full_sync** -- Pull tasks + pull comments for all tasks in a project

## Design Decisions

- Last-write-wins for conflicts (no merge logic)
- Errors per-item are collected in SyncResult.errors, sync continues
- SyncResult.merge() allows composing results from sub-operations
- get_by_external_id added to TaskService and TaskCommentService for upsert lookups

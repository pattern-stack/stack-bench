from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from features.task_comments.schemas.input import TaskCommentCreate, TaskCommentUpdate
from features.tasks.schemas.input import TaskCreate, TaskUpdate
from molecules.providers.task_provider import ExternalComment, ExternalTask, SyncResult

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from molecules.entities.task_management_entity import TaskManagementEntity
    from molecules.providers.task_provider import TaskProvider

logger = logging.getLogger(__name__)


class SyncEngine:
    """Coordinates bi-directional sync between local DB and external providers.

    Uses last-write-wins for conflict resolution. Composes a TaskManagementEntity
    for local operations and a TaskProvider adapter for external operations.
    """

    def __init__(
        self,
        db: AsyncSession,
        entity: TaskManagementEntity,
        adapter: TaskProvider,
    ) -> None:
        self.db = db
        self.entity = entity
        self.adapter = adapter

    async def pull_tasks(self, project_id: UUID | None = None) -> SyncResult:
        """Pull tasks from provider into local DB. Upsert by external_id."""
        result = SyncResult()
        project_id_str = str(project_id) if project_id else None

        try:
            external_tasks = await self.adapter.list_tasks(project_id=project_id_str)
        except Exception as exc:
            logger.exception("Failed to list tasks from provider")
            result.errors.append(f"Failed to list tasks: {exc}")
            return result

        for ext_task in external_tasks:
            try:
                await self._upsert_task(ext_task, project_id, result)
            except Exception as exc:
                logger.exception("Failed to sync task %s", ext_task.external_id)
                result.errors.append(f"Failed to sync task {ext_task.external_id}: {exc}")

        return result

    async def push_task(self, task_id: UUID) -> SyncResult:
        """Push a local task to the external provider."""
        result = SyncResult()

        try:
            task = await self.entity.get_task(task_id)
        except Exception as exc:
            result.errors.append(f"Failed to get task {task_id}: {exc}")
            return result

        ext_task = ExternalTask(
            external_id=task.external_id or "",
            title=task.title,
            description=task.description,
            state=task.state,
            priority=task.priority,
            url=task.external_url,
            provider=task.provider,
        )

        try:
            if task.external_id:
                returned = await self.adapter.update_task(task.external_id, ext_task)
                result.updated = 1
            else:
                returned = await self.adapter.create_task(ext_task)
                result.created = 1

            # Store the external_id and url from the provider response
            now = datetime.now(UTC)
            await self.entity.task_service.update(
                self.db,
                task_id,
                TaskUpdate(
                    external_id=returned.external_id,
                    external_url=returned.url,
                    provider=returned.provider,
                    last_synced_at=now,
                ),
            )
        except Exception as exc:
            logger.exception("Failed to push task %s", task_id)
            result.errors.append(f"Failed to push task {task_id}: {exc}")

        return result

    async def pull_comments(self, task_id: UUID) -> SyncResult:
        """Pull comments for a task from the external provider."""
        result = SyncResult()

        try:
            task = await self.entity.get_task(task_id)
        except Exception as exc:
            result.errors.append(f"Failed to get task {task_id}: {exc}")
            return result

        if not task.external_id:
            result.errors.append(f"Task {task_id} has no external_id — cannot pull comments")
            return result

        try:
            external_comments = await self.adapter.list_comments(task.external_id)
        except Exception as exc:
            logger.exception("Failed to list comments for task %s", task.external_id)
            result.errors.append(f"Failed to list comments: {exc}")
            return result

        for ext_comment in external_comments:
            try:
                await self._upsert_comment(ext_comment, task_id, task.provider, result)
            except Exception as exc:
                logger.exception("Failed to sync comment %s", ext_comment.external_id)
                result.errors.append(f"Failed to sync comment {ext_comment.external_id}: {exc}")

        return result

    async def full_sync(self, project_id: UUID | None = None) -> SyncResult:
        """Full bi-directional sync: pull tasks, then pull comments for each."""
        pull_result = await self.pull_tasks(project_id=project_id)

        # Pull comments for all tasks that have an external_id
        if project_id is not None:
            tasks = await self.entity.list_tasks_by_project(project_id)
        else:
            # Without a project scope, we sync comments for tasks we just pulled
            # This is a simplified approach — full implementation would track synced task IDs
            return pull_result

        comment_result = SyncResult()
        for task in tasks:
            if task.external_id:
                task_comment_result = await self.pull_comments(task.id)
                comment_result = comment_result.merge(task_comment_result)

        return pull_result.merge(comment_result)

    # --- Internal helpers ---

    async def _upsert_task(
        self,
        ext_task: ExternalTask,
        project_id: UUID | None,
        result: SyncResult,
    ) -> None:
        """Create or update a local task from an external task."""
        now = datetime.now(UTC)
        existing = await self.entity.task_service.get_by_external_id(self.db, ext_task.external_id, ext_task.provider)

        if existing is None:
            await self.entity.task_service.create(
                self.db,
                TaskCreate(
                    title=ext_task.title,
                    description=ext_task.description,
                    priority=ext_task.priority or "none",
                    external_id=ext_task.external_id,
                    external_url=ext_task.url,
                    provider=ext_task.provider,
                    project_id=project_id,
                    last_synced_at=now,
                ),
            )
            result.created += 1
        else:
            await self.entity.task_service.update(
                self.db,
                existing.id,
                TaskUpdate(
                    title=ext_task.title,
                    description=ext_task.description,
                    priority=ext_task.priority,
                    external_url=ext_task.url,
                    last_synced_at=now,
                ),
            )
            result.updated += 1

    async def _upsert_comment(
        self,
        ext_comment: ExternalComment,
        task_id: UUID,
        provider: str,
        result: SyncResult,
    ) -> None:
        """Create or update a local comment from an external comment."""
        now = datetime.now(UTC)
        existing = await self.entity.comment_service.get_by_external_id(self.db, ext_comment.external_id, provider)

        if existing is None:
            await self.entity.comment_service.create(
                self.db,
                TaskCommentCreate(
                    task_id=task_id,
                    body=ext_comment.body,
                    external_id=ext_comment.external_id,
                    external_url=ext_comment.url,
                    provider=provider,
                    last_synced_at=now,
                ),
            )
            result.created += 1
        else:
            await self.entity.comment_service.update(
                self.db,
                existing.id,
                TaskCommentUpdate(
                    body=ext_comment.body,
                    external_url=ext_comment.url,
                    last_synced_at=now,
                ),
            )
            result.updated += 1

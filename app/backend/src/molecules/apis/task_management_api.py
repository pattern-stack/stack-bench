from __future__ import annotations

from typing import TYPE_CHECKING

from features.sprints.schemas.output import SprintResponse
from features.task_comments.schemas.output import TaskCommentResponse
from features.task_projects.schemas.output import TaskProjectResponse
from features.task_relations.schemas.output import TaskRelationResponse
from features.task_tags.schemas.output import TaskTagResponse
from features.tasks.schemas.output import TaskResponse
from molecules.entities.task_management_entity import TaskManagementEntity
from molecules.exceptions import SyncNotConfiguredError
from molecules.services.sync_engine import SyncEngine

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from molecules.providers.task_provider import SyncResult, TaskProvider


class TaskManagementAPI:
    """API facade for task management domain.

    Coordinates TaskManagementEntity and SyncEngine, handles serialization
    to response models. Both REST and CLI consume this. Permissions will be
    added here when auth is implemented.
    """

    def __init__(self, db: AsyncSession, *, adapter: TaskProvider | None = None) -> None:
        self.db = db
        self.entity = TaskManagementEntity(db)
        self.sync: SyncEngine | None = SyncEngine(db, self.entity, adapter) if adapter else None

    # --- Task operations ---

    async def create_task(
        self,
        title: str,
        *,
        project_id: UUID | None = None,
        description: str | None = None,
        priority: str = "none",
        issue_type: str = "task",
        work_phase: str | None = None,
        status_category: str = "todo",
        assignee_id: UUID | None = None,
        sprint_id: UUID | None = None,
    ) -> TaskResponse:
        """Create a new task."""
        task = await self.entity.create_task(
            title,
            project_id=project_id,
            description=description,
            priority=priority,
            issue_type=issue_type,
            work_phase=work_phase,
            status_category=status_category,
            assignee_id=assignee_id,
            sprint_id=sprint_id,
        )
        await self.db.commit()
        return TaskResponse.model_validate(task)

    async def get_task(self, task_id: UUID) -> TaskResponse:
        """Get a task by ID."""
        task = await self.entity.get_task(task_id)
        return TaskResponse.model_validate(task)

    async def list_tasks(
        self,
        *,
        project_id: UUID | None = None,
        sprint_id: UUID | None = None,
    ) -> list[TaskResponse]:
        """List tasks filtered by project or sprint."""
        if sprint_id:
            tasks = await self.entity.list_tasks_by_sprint(sprint_id)
        elif project_id:
            tasks = await self.entity.list_tasks_by_project(project_id)
        else:
            tasks = []
        return [TaskResponse.model_validate(t) for t in tasks]

    async def update_task(
        self,
        task_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        issue_type: str | None = None,
        work_phase: str | None = None,
        status_category: str | None = None,
        assignee_id: UUID | None = None,
        sprint_id: UUID | None = None,
    ) -> TaskResponse:
        """Update a task's fields."""
        task = await self.entity.update_task(
            task_id,
            title=title,
            description=description,
            priority=priority,
            issue_type=issue_type,
            work_phase=work_phase,
            status_category=status_category,
            assignee_id=assignee_id,
            sprint_id=sprint_id,
        )
        await self.db.commit()
        return TaskResponse.model_validate(task)

    async def delete_task(self, task_id: UUID) -> None:
        """Soft-delete a task."""
        await self.entity.delete_task(task_id)
        await self.db.commit()

    async def transition_task(self, task_id: UUID, new_state: str) -> TaskResponse:
        """Transition a task to a new state."""
        task = await self.entity.transition_task(task_id, new_state)
        await self.db.commit()
        return TaskResponse.model_validate(task)

    # --- Project operations ---

    async def create_project(
        self,
        name: str,
        *,
        description: str | None = None,
        lead_id: UUID | None = None,
    ) -> TaskProjectResponse:
        """Create a new task project."""
        project = await self.entity.create_project(
            name,
            description=description,
            lead_id=lead_id,
        )
        await self.db.commit()
        return TaskProjectResponse.model_validate(project)

    async def get_project(self, project_id: UUID) -> TaskProjectResponse:
        """Get a project by ID."""
        project = await self.entity.get_project(project_id)
        return TaskProjectResponse.model_validate(project)

    async def list_projects(self) -> list[TaskProjectResponse]:
        """List all projects."""
        projects = await self.entity.list_projects()
        return [TaskProjectResponse.model_validate(p) for p in projects]

    # --- Sprint operations ---

    async def create_sprint(
        self,
        name: str,
        *,
        project_id: UUID | None = None,
        number: int | None = None,
        description: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
    ) -> SprintResponse:
        """Create a new sprint."""
        sprint = await self.entity.create_sprint(
            name,
            project_id=project_id,
            number=number,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        await self.db.commit()
        return SprintResponse.model_validate(sprint)

    async def get_sprint(self, sprint_id: UUID) -> SprintResponse:
        """Get a sprint by ID."""
        sprint = await self.entity.get_sprint(sprint_id)
        return SprintResponse.model_validate(sprint)

    async def get_active_sprint(self, project_id: UUID) -> SprintResponse | None:
        """Get the active sprint for a project, or None."""
        sprint = await self.entity.get_active_sprint(project_id)
        if sprint is None:
            return None
        return SprintResponse.model_validate(sprint)

    async def list_sprints(self, project_id: UUID) -> list[SprintResponse]:
        """List all sprints for a project."""
        sprints = await self.entity.list_sprints_by_project(project_id)
        return [SprintResponse.model_validate(s) for s in sprints]

    # --- Comment operations ---

    async def add_comment(
        self,
        task_id: UUID,
        body: str,
        *,
        author_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> TaskCommentResponse:
        """Add a comment to a task."""
        comment = await self.entity.add_comment(
            task_id,
            body,
            author_id=author_id,
            parent_id=parent_id,
        )
        await self.db.commit()
        return TaskCommentResponse.model_validate(comment)

    async def list_comments(self, task_id: UUID) -> list[TaskCommentResponse]:
        """List all comments for a task."""
        comments = await self.entity.list_comments(task_id)
        return [TaskCommentResponse.model_validate(c) for c in comments]

    # --- Tag operations ---

    async def apply_tag(self, task_id: UUID, tag_id: UUID) -> None:
        """Apply a tag to a task."""
        await self.entity.apply_tag(task_id, tag_id)
        await self.db.commit()

    async def remove_tag(self, task_id: UUID, tag_id: UUID) -> None:
        """Remove a tag from a task."""
        await self.entity.remove_tag(task_id, tag_id)
        await self.db.commit()

    async def get_task_tags(self, task_id: UUID) -> list[TaskTagResponse]:
        """Get all tags for a task."""
        tags = await self.entity.get_task_tags(task_id)
        return [TaskTagResponse.model_validate(t) for t in tags]

    # --- Relation operations ---

    async def add_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
    ) -> TaskRelationResponse:
        """Add a relation between two tasks."""
        relation = await self.entity.add_relation(source_id, target_id, relation_type)
        await self.db.commit()
        return TaskRelationResponse.model_validate(relation)

    async def get_task_relations(self, task_id: UUID) -> list[TaskRelationResponse]:
        """Get all relations for a task."""
        relations = await self.entity.get_task_relations(task_id)
        return [TaskRelationResponse.model_validate(r) for r in relations]

    async def get_blockers(self, task_id: UUID) -> list[TaskRelationResponse]:
        """Get all relations that block a task."""
        blockers = await self.entity.get_blockers(task_id)
        return [TaskRelationResponse.model_validate(b) for b in blockers]

    # --- Sync operations ---

    async def sync_tasks(self, project_id: UUID | None = None) -> SyncResult:
        """Full sync: pull tasks and comments from external provider."""
        if self.sync is None:
            raise SyncNotConfiguredError()
        result = await self.sync.full_sync(project_id=project_id)
        await self.db.commit()
        return result

    async def sync_task(self, task_id: UUID) -> SyncResult:
        """Push a single task to the external provider."""
        if self.sync is None:
            raise SyncNotConfiguredError()
        result = await self.sync.push_task(task_id)
        await self.db.commit()
        return result

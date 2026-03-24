from __future__ import annotations

from typing import TYPE_CHECKING

from features.sprints.schemas.input import SprintCreate
from features.sprints.service import SprintService
from features.task_comments.schemas.input import TaskCommentCreate
from features.task_comments.service import TaskCommentService
from features.task_projects.schemas.input import TaskProjectCreate
from features.task_projects.service import TaskProjectService
from features.task_relations.schemas.input import TaskRelationCreate
from features.task_relations.service import TaskRelationService
from features.task_tags.service import TaskTagService
from features.tasks.schemas.input import TaskCreate, TaskUpdate
from features.tasks.service import TaskService
from molecules.exceptions import (
    RelationCycleError,
    SprintNotFoundError,
    TaskHasBlockersError,
    TaskNotFoundError,
    TaskProjectNotFoundError,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from features.sprints.models import Sprint
    from features.task_comments.models import TaskComment
    from features.task_projects.models import TaskProject
    from features.task_relations.models import TaskRelation
    from features.task_tags.models import TaskTag
    from features.tasks.models import Task


class TaskManagementEntity:
    """Domain aggregate for task management lifecycle.

    Coordinates six feature services: tasks, projects, sprints,
    comments, tags, and relations into a single domain concept.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.task_service = TaskService()
        self.project_service = TaskProjectService()
        self.sprint_service = SprintService()
        self.comment_service = TaskCommentService()
        self.tag_service = TaskTagService()
        self.relation_service = TaskRelationService()

    # --- Task lifecycle ---

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
    ) -> Task:
        """Create a new task."""
        task = await self.task_service.create(
            self.db,
            TaskCreate(
                title=title,
                project_id=project_id,
                description=description,
                priority=priority,
                issue_type=issue_type,
                work_phase=work_phase,
                status_category=status_category,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
            ),
        )
        return task

    async def get_task(self, task_id: UUID) -> Task:
        """Get a task by ID or raise."""
        task = await self.task_service.get(self.db, task_id)
        if task is None or task.is_deleted:
            raise TaskNotFoundError(task_id)
        return task

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
    ) -> Task:
        """Update a task's fields."""
        await self.get_task(task_id)  # Validate task exists
        updated = await self.task_service.update(
            self.db,
            task_id,
            TaskUpdate(
                title=title,
                description=description,
                priority=priority,
                issue_type=issue_type,
                work_phase=work_phase,
                status_category=status_category,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
            ),
        )
        return updated

    async def delete_task(self, task_id: UUID) -> None:
        """Soft-delete a task, but check for open blockers first."""
        task = await self.get_task(task_id)

        # Check for open blockers
        blockers = await self.relation_service.get_blockers(self.db, task_id)
        open_blocker_ids: list[UUID] = []
        for blocker in blockers:
            source_task = await self.task_service.get(self.db, blocker.source_task_id)
            if (
                source_task is not None
                and not source_task.is_deleted
                and source_task.state not in ("done", "cancelled")
            ):
                open_blocker_ids.append(blocker.source_task_id)

        if open_blocker_ids:
            raise TaskHasBlockersError(task_id, open_blocker_ids)

        task.soft_delete()
        await self.db.flush()

    async def list_tasks_by_project(self, project_id: UUID) -> list[Task]:
        """List all tasks for a project."""
        return await self.task_service.list_by_project(self.db, project_id)

    async def list_tasks_by_sprint(self, sprint_id: UUID) -> list[Task]:
        """List all tasks for a sprint."""
        return await self.task_service.list_by_sprint(self.db, sprint_id)

    async def transition_task(self, task_id: UUID, new_state: str) -> Task:
        """Transition a task to a new state using EventPattern.transition."""
        task = await self.get_task(task_id)
        task.transition_to(new_state)
        await self.db.flush()
        return task

    # --- Project operations ---

    async def create_project(
        self,
        name: str,
        *,
        description: str | None = None,
        lead_id: UUID | None = None,
    ) -> TaskProject:
        """Create a new task project."""
        project = await self.project_service.create(
            self.db,
            TaskProjectCreate(
                name=name,
                description=description,
                lead_id=lead_id,
            ),
        )
        return project

    async def get_project(self, project_id: UUID) -> TaskProject:
        """Get a project by ID or raise."""
        project = await self.project_service.get(self.db, project_id)
        if project is None or project.is_deleted:
            raise TaskProjectNotFoundError(project_id)
        return project

    async def list_projects(self) -> list[TaskProject]:
        """List all projects."""
        projects, _count = await self.project_service.list(self.db)
        return projects

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
    ) -> Sprint:
        """Create a new sprint."""
        sprint = await self.sprint_service.create(
            self.db,
            SprintCreate(
                name=name,
                project_id=project_id,
                number=number,
                description=description,
                starts_at=starts_at,
                ends_at=ends_at,
            ),
        )
        return sprint

    async def get_sprint(self, sprint_id: UUID) -> Sprint:
        """Get a sprint by ID or raise."""
        sprint = await self.sprint_service.get(self.db, sprint_id)
        if sprint is None or sprint.is_deleted:
            raise SprintNotFoundError(sprint_id)
        return sprint

    async def get_active_sprint(self, project_id: UUID) -> Sprint | None:
        """Get the active sprint for a project, or None."""
        return await self.sprint_service.get_active_sprint(self.db, project_id)

    async def list_sprints_by_project(self, project_id: UUID) -> list[Sprint]:
        """List all sprints for a project."""
        return await self.sprint_service.list_by_project(self.db, project_id)

    # --- Comment operations ---

    async def add_comment(
        self,
        task_id: UUID,
        body: str,
        *,
        author_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> TaskComment:
        """Add a comment to a task."""
        await self.get_task(task_id)  # Validate task exists
        comment = await self.comment_service.create(
            self.db,
            TaskCommentCreate(
                task_id=task_id,
                body=body,
                author_id=author_id,
                parent_id=parent_id,
            ),
        )
        return comment

    async def list_comments(self, task_id: UUID) -> list[TaskComment]:
        """List all comments for a task."""
        return await self.comment_service.list_by_task(self.db, task_id)

    # --- Tag operations ---

    async def apply_tag(self, task_id: UUID, tag_id: UUID) -> None:
        """Apply a tag to a task, enforcing exclusivity within groups."""
        await self.get_task(task_id)  # Validate task exists

        tag = await self.tag_service.get(self.db, tag_id)
        if tag is None:
            return

        # Enforce exclusivity: if this tag is exclusive and has a group,
        # remove other tags from the same group first
        if tag.is_exclusive and tag.group:
            current_tags = await self.tag_service.get_task_tags(self.db, task_id)
            for current_tag in current_tags:
                if current_tag.group == tag.group and current_tag.id != tag_id:
                    await self.tag_service.remove_tag(self.db, task_id, current_tag.id)

        await self.tag_service.apply_tag(self.db, task_id, tag_id)

    async def remove_tag(self, task_id: UUID, tag_id: UUID) -> None:
        """Remove a tag from a task."""
        await self.tag_service.remove_tag(self.db, task_id, tag_id)

    async def get_task_tags(self, task_id: UUID) -> list[TaskTag]:
        """Get all tags for a task."""
        return await self.tag_service.get_task_tags(self.db, task_id)

    # --- Relation operations ---

    async def add_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
    ) -> TaskRelation:
        """Add a relation between two tasks with cycle detection."""
        # Cycle detection for parent_of and blocks
        if relation_type in ("parent_of", "blocks"):
            await self._detect_cycle(source_id, target_id, relation_type)

        relation = await self.relation_service.create(
            self.db,
            TaskRelationCreate(
                source_task_id=source_id,
                target_task_id=target_id,
                relation_type=relation_type,
            ),
        )
        return relation

    async def get_task_relations(self, task_id: UUID) -> list[TaskRelation]:
        """Get all relations for a task."""
        return await self.relation_service.get_task_relations(self.db, task_id)

    async def get_blockers(self, task_id: UUID) -> list[TaskRelation]:
        """Get all relations that block a task."""
        return await self.relation_service.get_blockers(self.db, task_id)

    # --- Internal helpers ---

    async def _detect_cycle(self, source_id: UUID, target_id: UUID, relation_type: str) -> None:
        """Walk the relation graph to detect cycles before creating a new relation.

        For 'parent_of': source is parent of target. A cycle exists if target
        is already an ancestor of source (walking parent_of from source upward).

        For 'blocks': source blocks target. A cycle exists if target already
        blocks source (walking blocks from source upward).
        """
        visited: set[UUID] = set()
        current_id: UUID | None = source_id

        while current_id is not None:
            if current_id == target_id:
                raise RelationCycleError(source_id, target_id, relation_type)
            if current_id in visited:
                break
            visited.add(current_id)

            # Walk up: find where current_id is the target of the same relation_type
            relations = await self.relation_service.get_task_relations(self.db, current_id)
            parent_id: UUID | None = None
            for rel in relations:
                if rel.relation_type == relation_type and rel.target_task_id == current_id:
                    parent_id = rel.source_task_id
                    break
            current_id = parent_id

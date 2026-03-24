from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskRelation
from .schemas.input import TaskRelationCreate, TaskRelationUpdate

_created_at = TaskRelation.__table__.c.created_at


class TaskRelationService(BaseService[TaskRelation, TaskRelationCreate, TaskRelationUpdate]):
    model = TaskRelation

    async def get_task_relations(self, db: AsyncSession, task_id: UUID) -> list[TaskRelation]:
        """Return all relations where task is source OR target."""
        result = await db.execute(
            select(TaskRelation)
            .where(
                or_(
                    TaskRelation.source_task_id == task_id,
                    TaskRelation.target_task_id == task_id,
                )
            )
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def get_blockers(self, db: AsyncSession, task_id: UUID) -> list[TaskRelation]:
        """Return relations where target=task_id and type='blocks' (tasks that block this task)."""
        result = await db.execute(
            select(TaskRelation)
            .where(TaskRelation.target_task_id == task_id)
            .where(TaskRelation.relation_type == "blocks")
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def get_children(self, db: AsyncSession, task_id: UUID) -> list[TaskRelation]:
        """Return relations where source=task_id and type='parent_of' (child tasks)."""
        result = await db.execute(
            select(TaskRelation)
            .where(TaskRelation.source_task_id == task_id)
            .where(TaskRelation.relation_type == "parent_of")
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def get_parent(self, db: AsyncSession, task_id: UUID) -> TaskRelation | None:
        """Return the relation where target=task_id and type='parent_of' (parent task)."""
        result = await db.execute(
            select(TaskRelation)
            .where(TaskRelation.target_task_id == task_id)
            .where(TaskRelation.relation_type == "parent_of")
            .limit(1)
        )
        return result.scalar_one_or_none()

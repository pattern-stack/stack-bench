from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskComment
from .schemas.input import TaskCommentCreate, TaskCommentUpdate


class TaskCommentService(BaseService[TaskComment, TaskCommentCreate, TaskCommentUpdate]):
    model = TaskComment

    async def get_by_external_id(self, db: AsyncSession, external_id: str, provider: str) -> TaskComment | None:
        _deleted_at = TaskComment.__table__.c.deleted_at
        result = await db.execute(
            select(TaskComment)
            .where(TaskComment.external_id == external_id)
            .where(TaskComment.provider == provider)
            .where(_deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_task(self, db: AsyncSession, task_id: UUID) -> list[TaskComment]:
        result = await db.execute(
            select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_author(self, db: AsyncSession, author_id: UUID) -> list[TaskComment]:
        result = await db.execute(
            select(TaskComment).where(TaskComment.author_id == author_id).order_by(TaskComment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_thread(self, db: AsyncSession, parent_id: UUID) -> list[TaskComment]:
        result = await db.execute(
            select(TaskComment).where(TaskComment.parent_id == parent_id).order_by(TaskComment.created_at.asc())
        )
        return list(result.scalars().all())

from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Task
from .schemas.input import TaskCreate, TaskUpdate

_deleted_at = Task.__table__.c.deleted_at
_created_at = Task.__table__.c.created_at


class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    model = Task

    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task).where(Task.project_id == project_id).where(_deleted_at.is_(None)).order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_sprint(self, db: AsyncSession, sprint_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task).where(Task.sprint_id == sprint_id).where(_deleted_at.is_(None)).order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_assignee(self, db: AsyncSession, assignee_id: UUID) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.assignee_id == assignee_id)
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_external_id(self, db: AsyncSession, external_id: str, provider: str) -> Task | None:
        result = await db.execute(
            select(Task)
            .where(Task.external_id == external_id)
            .where(Task.provider == provider)
            .where(_deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def search_by_title(self, db: AsyncSession, query: str, limit: int = 20) -> list[Task]:
        result = await db.execute(
            select(Task)
            .where(Task.title.ilike(f"%{query}%"))
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

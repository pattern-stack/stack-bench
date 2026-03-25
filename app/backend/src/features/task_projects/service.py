from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskProject
from .schemas.input import TaskProjectCreate, TaskProjectUpdate

_deleted_at = TaskProject.__table__.c.deleted_at
_created_at = TaskProject.__table__.c.created_at
_state = TaskProject.__table__.c.state


class TaskProjectService(BaseService[TaskProject, TaskProjectCreate, TaskProjectUpdate]):
    model = TaskProject

    async def list_by_status(self, db: AsyncSession, state: str) -> list[TaskProject]:
        result = await db.execute(
            select(TaskProject).where(_state == state).where(_deleted_at.is_(None)).order_by(_created_at.desc())
        )
        return list(result.scalars().all())

    async def search_by_name(self, db: AsyncSession, query: str, limit: int = 20) -> list[TaskProject]:
        result = await db.execute(
            select(TaskProject)
            .where(TaskProject.name.ilike(f"%{query}%"))
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

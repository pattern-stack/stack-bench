from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Sprint
from .schemas.input import SprintCreate, SprintUpdate

_deleted_at = Sprint.__table__.c.deleted_at
_created_at = Sprint.__table__.c.created_at
_state = Sprint.__table__.c.state


class SprintService(BaseService[Sprint, SprintCreate, SprintUpdate]):
    model = Sprint

    async def get_active_sprint(self, db: AsyncSession, project_id: UUID) -> Sprint | None:
        result = await db.execute(
            select(Sprint)
            .where(Sprint.project_id == project_id)
            .where(_state == "active")
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> list[Sprint]:
        result = await db.execute(
            select(Sprint)
            .where(Sprint.project_id == project_id)
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return list(result.scalars().all())

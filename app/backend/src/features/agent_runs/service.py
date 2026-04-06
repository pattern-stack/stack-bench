from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentRun
from .schemas.input import AgentRunCreate, AgentRunUpdate

_deleted_at = AgentRun.__table__.c.deleted_at
_created_at = AgentRun.__table__.c.created_at


class AgentRunService(BaseService[AgentRun, AgentRunCreate, AgentRunUpdate]):
    model = AgentRun

    async def list_by_job(self, db: AsyncSession, job_id: UUID) -> list[AgentRun]:
        result = await db.execute(
            select(AgentRun).where(AgentRun.job_id == job_id).where(_deleted_at.is_(None)).order_by(_created_at.asc())
        )
        return list(result.scalars().all())

from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Job
from .schemas.input import JobCreate, JobUpdate

_deleted_at = Job.__table__.c.deleted_at
_created_at = Job.__table__.c.created_at


class JobService(BaseService[Job, JobCreate, JobUpdate]):
    model = Job

    async def list_by_task(self, db: AsyncSession, task_id: UUID) -> list[Job]:
        result = await db.execute(
            select(Job).where(Job.task_id == task_id).where(_deleted_at.is_(None)).order_by(_created_at.desc())
        )
        return list(result.scalars().all())

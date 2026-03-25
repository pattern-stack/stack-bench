from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CascadeStep
from .schemas.input import CascadeStepCreate, CascadeStepUpdate

_deleted_at = CascadeStep.__table__.c.deleted_at
_state = CascadeStep.__table__.c.state


class CascadeStepService(BaseService[CascadeStep, CascadeStepCreate, CascadeStepUpdate]):
    model = CascadeStep

    async def list_by_cascade(self, db: AsyncSession, cascade_id: UUID) -> list[CascadeStep]:
        """Get all steps for a cascade, ordered by position."""
        result = await db.execute(
            select(CascadeStep)
            .where(CascadeStep.cascade_id == cascade_id)
            .where(_deleted_at.is_(None))
            .order_by(CascadeStep.position)
        )
        return list(result.scalars().all())

    async def get_by_head_sha(self, db: AsyncSession, head_sha: str) -> CascadeStep | None:
        """Find a cascade step by its head SHA."""
        result = await db.execute(
            select(CascadeStep).where(CascadeStep.head_sha == head_sha).where(_deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_pull_request(self, db: AsyncSession, pull_request_id: UUID) -> CascadeStep | None:
        """Find a cascade step by its pull request ID."""
        result = await db.execute(
            select(CascadeStep).where(CascadeStep.pull_request_id == pull_request_id).where(_deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_pending_step(self, db: AsyncSession, cascade_id: UUID) -> CascadeStep | None:
        """Get the next pending step in a cascade."""
        result = await db.execute(
            select(CascadeStep)
            .where(CascadeStep.cascade_id == cascade_id)
            .where(_state == "pending")
            .where(_deleted_at.is_(None))
            .order_by(CascadeStep.position)
        )
        return result.scalars().first()

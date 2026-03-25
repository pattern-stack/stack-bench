from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MergeCascade
from .schemas.input import MergeCascadeCreate, MergeCascadeUpdate

_deleted_at = MergeCascade.__table__.c.deleted_at
_created_at = MergeCascade.__table__.c.created_at
_state = MergeCascade.__table__.c.state


class MergeCascadeService(BaseService[MergeCascade, MergeCascadeCreate, MergeCascadeUpdate]):
    model = MergeCascade

    async def get_active_for_stack(self, db: AsyncSession, stack_id: UUID) -> MergeCascade | None:
        """Find the running or pending cascade for a stack."""
        result = await db.execute(
            select(MergeCascade)
            .where(MergeCascade.stack_id == stack_id)
            .where(_state.in_(["pending", "running"]))
            .where(_deleted_at.is_(None))
            .order_by(_created_at.desc())
        )
        return result.scalar_one_or_none()

from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CheckRun
from .schemas.input import CheckRunCreate, CheckRunUpdate


class CheckRunService(BaseService[CheckRun, CheckRunCreate, CheckRunUpdate]):
    model = CheckRun

    async def get_by_external_id(self, db: AsyncSession, external_id: int) -> CheckRun | None:
        """Get a check run by its GitHub check run ID."""
        result = await db.execute(select(CheckRun).where(CheckRun.external_id == external_id))
        return result.scalar_one_or_none()

    async def get_by_pull_request(self, db: AsyncSession, pull_request_id: UUID) -> list[CheckRun]:
        """Get all check runs for a pull request."""
        result = await db.execute(
            select(CheckRun).where(CheckRun.pull_request_id == pull_request_id).order_by(CheckRun.created_at)
        )
        return list(result.scalars().all())

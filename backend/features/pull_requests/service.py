from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PullRequest
from .schemas.input import PullRequestCreate, PullRequestUpdate


class PullRequestService(BaseService[PullRequest, PullRequestCreate, PullRequestUpdate]):
    model = PullRequest

    async def get_by_branch(
        self, db: AsyncSession, branch_id: UUID
    ) -> PullRequest | None:
        """Get the pull request for a branch (1:1 relationship)."""
        result = await db.execute(
            select(PullRequest)
            .where(PullRequest.branch_id == branch_id)
            .where(PullRequest.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self, db: AsyncSession, external_id: int
    ) -> PullRequest | None:
        """Get a pull request by its GitHub PR number."""
        result = await db.execute(
            select(PullRequest)
            .where(PullRequest.external_id == external_id)
            .where(PullRequest.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

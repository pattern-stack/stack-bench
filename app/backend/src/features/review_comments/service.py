from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ReviewComment
from .schemas.input import ReviewCommentCreate, ReviewCommentUpdate


class ReviewCommentService(BaseService[ReviewComment, ReviewCommentCreate, ReviewCommentUpdate]):
    model = ReviewComment

    async def list_by_branch(self, db: AsyncSession, branch_id: UUID) -> list[ReviewComment]:
        """Get all comments for a branch, ordered by creation time."""
        result = await db.execute(
            select(ReviewComment).where(ReviewComment.branch_id == branch_id).order_by(ReviewComment.created_at)
        )
        return list(result.scalars().all())

from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Branch
from .schemas.input import BranchCreate, BranchUpdate


class BranchService(BaseService[Branch, BranchCreate, BranchUpdate]):
    model = Branch

    async def list_by_stack(
        self, db: AsyncSession, stack_id: UUID
    ) -> list[Branch]:
        """Get all branches for a stack, ordered by position."""
        result = await db.execute(
            select(Branch)
            .where(Branch.stack_id == stack_id)
            .where(Branch.deleted_at.is_(None))
            .order_by(Branch.position)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, db: AsyncSession, stack_id: UUID, name: str
    ) -> Branch | None:
        """Get a branch by stack and git branch name."""
        result = await db.execute(
            select(Branch)
            .where(Branch.stack_id == stack_id)
            .where(Branch.name == name)
            .where(Branch.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_max_position(
        self, db: AsyncSession, stack_id: UUID
    ) -> int:
        """Get the highest position in a stack (0 if no branches)."""
        from sqlalchemy import func

        result = await db.execute(
            select(func.coalesce(func.max(Branch.position), 0)).where(
                Branch.stack_id == stack_id
            )
        )
        return result.scalar_one()

    async def list_by_workspace(
        self, db: AsyncSession, workspace_id: UUID
    ) -> list[Branch]:
        """Get all branches in a workspace."""
        result = await db.execute(
            select(Branch)
            .where(Branch.workspace_id == workspace_id)
            .where(Branch.deleted_at.is_(None))
            .order_by(Branch.created_at)
        )
        return list(result.scalars().all())

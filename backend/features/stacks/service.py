from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Stack
from .schemas.input import StackCreate, StackUpdate


class StackService(BaseService[Stack, StackCreate, StackUpdate]):
    model = Stack

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID
    ) -> list[Stack]:
        """Get all stacks for a project."""
        result = await db.execute(
            select(Stack)
            .where(Stack.project_id == project_id)
            .where(Stack.deleted_at.is_(None))
            .order_by(Stack.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, db: AsyncSession, project_id: UUID, name: str
    ) -> Stack | None:
        """Get a stack by project and name."""
        result = await db.execute(
            select(Stack)
            .where(Stack.project_id == project_id)
            .where(Stack.name == name)
            .where(Stack.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_dependents(
        self, db: AsyncSession, branch_id: UUID
    ) -> list[Stack]:
        """Get stacks that depend on a given branch (via base_branch_id)."""
        result = await db.execute(
            select(Stack)
            .where(Stack.base_branch_id == branch_id)
            .where(Stack.deleted_at.is_(None))
        )
        return list(result.scalars().all())

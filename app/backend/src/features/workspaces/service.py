from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Workspace
from .schemas.input import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService(BaseService[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    async def list_by_project(self, db: AsyncSession, project_id: UUID, active_only: bool = True) -> list[Workspace]:
        query = select(Workspace).where(Workspace.project_id == project_id)
        if active_only:
            query = query.where(Workspace.is_active == True)  # noqa: E712
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_repo_url(self, db: AsyncSession, repo_url: str) -> Workspace | None:
        result = await db.execute(select(Workspace).where(Workspace.repo_url == repo_url))
        return result.scalar_one_or_none()

    async def get_by_project(self, db: AsyncSession, project_id: UUID) -> Workspace | None:
        """Get a single workspace for a project (convenience for 1:1 relationship)."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.project_id == project_id)
            .where(Workspace.deleted_at.is_(None))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_ready(self, db: AsyncSession, project_id: UUID) -> list[Workspace]:
        """List workspaces in 'ready' state for a project."""
        result = await db.execute(
            select(Workspace)
            .where(Workspace.project_id == project_id)
            .where(Workspace.state == "ready")
            .where(Workspace.deleted_at.is_(None))
        )
        return list(result.scalars().all())

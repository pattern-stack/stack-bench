from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Workspace
from .schemas.input import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService(BaseService[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID, active_only: bool = True
    ) -> list[Workspace]:
        query = select(Workspace).where(Workspace.project_id == project_id)
        if active_only:
            query = query.where(Workspace.is_active == True)  # noqa: E712
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_repo_url(self, db: AsyncSession, repo_url: str) -> Workspace | None:
        result = await db.execute(select(Workspace).where(Workspace.repo_url == repo_url))
        return result.scalar_one_or_none()

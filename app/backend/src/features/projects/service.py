from uuid import UUID

from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Project
from .schemas.input import ProjectCreate, ProjectUpdate

_deleted_at = Project.__table__.c.deleted_at


class ProjectService(BaseService[Project, ProjectCreate, ProjectUpdate]):
    model = Project

    async def get_by_name(self, db: AsyncSession, name: str) -> Project | None:
        result = await db.execute(select(Project).where(Project.name == name))
        return result.scalar_one_or_none()

    async def get_by_owner(self, db: AsyncSession, owner_id: UUID) -> list[Project]:
        result = await db.execute(
            select(Project).where(
                Project.owner_id == owner_id,
                _deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

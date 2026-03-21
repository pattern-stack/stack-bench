from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Project
from .schemas.input import ProjectCreate, ProjectUpdate


class ProjectService(BaseService[Project, ProjectCreate, ProjectUpdate]):
    model = Project

    async def get_by_name(self, db: AsyncSession, name: str) -> Project | None:
        result = await db.execute(select(Project).where(Project.name == name))
        return result.scalar_one_or_none()

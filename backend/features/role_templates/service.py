from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RoleTemplate
from .schemas.input import RoleTemplateCreate, RoleTemplateUpdate


class RoleTemplateService(BaseService[RoleTemplate, RoleTemplateCreate, RoleTemplateUpdate]):  # type: ignore[misc]
    model = RoleTemplate

    async def get_by_name(self, db: AsyncSession, name: str) -> RoleTemplate | None:
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == name))
        return result.scalar_one_or_none()

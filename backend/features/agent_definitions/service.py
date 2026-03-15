from pattern_stack.atoms.patterns.services import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgentDefinition
from .schemas.input import AgentDefinitionCreate, AgentDefinitionUpdate


class AgentDefinitionService(BaseService[AgentDefinition, AgentDefinitionCreate, AgentDefinitionUpdate]):
    model = AgentDefinition

    async def get_by_name(self, db: AsyncSession, name: str) -> AgentDefinition | None:
        result = await db.execute(select(AgentDefinition).where(AgentDefinition.name == name))
        return result.scalar_one_or_none()

    async def list_active(self, db: AsyncSession) -> list[AgentDefinition]:
        result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

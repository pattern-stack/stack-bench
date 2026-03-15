from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from features.agent_definitions.service import AgentDefinitionService
from features.role_templates.service import RoleTemplateService
from molecules.exceptions import AgentNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AgentConfig:
    """Runtime agent configuration assembled from DB definitions."""

    name: str
    role_name: str
    model: str
    persona: dict[str, Any]
    mission: str
    background: str | None
    awareness: dict[str, Any]


class AgentAssembler:
    """Loads stored definitions and builds agent configurations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._role_service = RoleTemplateService()
        self._agent_service = AgentDefinitionService()

    async def assemble(
        self,
        agent_name: str,
        *,
        model_override: str | None = None,
    ) -> AgentConfig:
        """Load an AgentDefinition by name and assemble config.

        Raises:
            AgentNotFoundError: If the agent or role template is not found/inactive.
        """
        agent_def = await self._agent_service.get_by_name(self.db, agent_name)
        if agent_def is None or not agent_def.is_active:
            available = await self.list_available()
            raise AgentNotFoundError(agent_name, available)

        role_tmpl = await self._role_service.get(self.db, agent_def.role_template_id)
        if role_tmpl is None or not role_tmpl.is_active:
            raise AgentNotFoundError(
                agent_name,
                await self.list_available(),
            )

        model = model_override or agent_def.model_override or role_tmpl.default_model or "claude-sonnet-4-20250514"

        return AgentConfig(
            name=agent_def.name,
            role_name=role_tmpl.name,
            model=model,
            persona=cast("dict[str, Any]", role_tmpl.persona),
            mission=agent_def.mission,
            background=agent_def.background,
            awareness=cast("dict[str, Any]", agent_def.awareness),
        )

    async def list_available(self) -> list[str]:
        """List names of active agent definitions."""
        defs = await self._agent_service.list_active(self.db)
        return [d.name for d in defs]

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.datatypes import Awareness, Background, Mission, Persona
from agentic_patterns.core.organisms.agents import Agent, AgentBuilder
from agentic_patterns.core.organisms.roles import RoleBuilder
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
            persona=role_tmpl.persona,
            mission=agent_def.mission,
            background=agent_def.background,
            awareness=agent_def.awareness,
        )

    async def build_agent(
        self,
        agent_name: str,
        *,
        model_override: str | None = None,
    ) -> Agent:
        """Assemble config and build a canonical agentic-patterns Agent.

        Uses RoleBuilder and AgentBuilder per ADR-001.
        """
        config = await self.assemble(agent_name, model_override=model_override)

        persona = Persona(
            identity=config.persona.get("identity", config.persona.get("name", "AI Assistant")),
            tone=config.persona.get("tone", "professional and helpful"),
            priorities=config.persona.get("priorities", []),
            principles=config.persona.get("principles", []),
        )

        role = (
            RoleBuilder(config.role_name)
            .with_persona(persona)
            .with_default_model(config.model)
            .build()
        )

        background = Background(**config.background) if isinstance(config.background, dict) else Background()

        awareness = Awareness(**config.awareness) if config.awareness else Awareness()

        mission = Mission(objective=config.mission)

        return (
            AgentBuilder(role)
            .with_background(background)
            .with_awareness(awareness)
            .with_mission(mission)
            .with_model(config.model)
            .build()
        )

    async def list_available(self) -> list[str]:
        """List names of active agent definitions."""
        defs = await self._agent_service.list_active(self.db)
        return [d.name for d in defs]

"""AgentFactory — converts DB AgentConfig to agentic-patterns Agent.

Bridges the gap between stack-bench's stored agent definitions (assembled
by AgentAssembler) and agentic-patterns' runtime Agent dataclass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_patterns.core.atoms.datatypes import Mission, Persona
from agentic_patterns.core.organisms.agents import Agent
from agentic_patterns.core.organisms.roles import Role

if TYPE_CHECKING:
    from molecules.agents.assembler import AgentConfig


class AgentFactory:
    """Converts a stack-bench AgentConfig into an agentic-patterns Agent."""

    @staticmethod
    def create(config: AgentConfig) -> Agent:
        """Build an agentic-patterns Agent from a DB-assembled AgentConfig.

        Args:
            config: AgentConfig from AgentAssembler.assemble()

        Returns:
            Fully constructed Agent ready for a runner.
        """
        persona = AgentFactory._build_persona(config.persona)

        role = Role(
            name=config.role_name,
            persona=persona,
            default_model=config.model,
        )

        mission = Mission(objective=config.mission)

        return Agent(
            role=role,
            mission=mission,
            model=config.model,
        )

    @staticmethod
    def _build_persona(persona_data: dict[str, Any]) -> Persona:
        """Build a Persona from a DB persona dict.

        Handles varying shapes of persona data stored in the DB.
        Provides sensible defaults for required fields.

        Args:
            persona_data: Dict from RoleTemplate.persona column

        Returns:
            Persona instance
        """
        identity = persona_data.get("identity", persona_data.get("name", "AI Assistant"))
        tone = persona_data.get("tone", "professional and helpful")

        return Persona(
            identity=identity,
            tone=tone,
            priorities=persona_data.get("priorities", []),
            principles=persona_data.get("principles", []),
        )
